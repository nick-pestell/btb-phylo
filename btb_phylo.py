import argparse
import json
from os import path

import utils
import update_summary
import filter_samples
import phylogeny

def update_samples(summary_filepath=utils.DEFAULT_SUMMARY_FILEPATH):
    """
        Updates the local copy of the sample summary csv file containing metadata 
        for all samples file or builds a new one from scratch if it does not 
        already exist. Downloads all FinalOut.csv files from s3-csu-003 and appends 
        them to the a pandas DataFrame and saves the data to csv.

        Parameters:
            summary_filepath (str): path to location of summary csv  
    """
    print("\nupdate_summary\n")
    print("Loading summary csv file ... \n")
    # download sample summary csv
    df_summary = update_summary.get_df_summary(summary_filepath)
    print("Getting s3 keys for batch summary files ... \n")
    # get s3 keys of FinalOut.csv for new batches of samples
    new_keys = update_summary.new_final_out_keys(df_summary)
    print("Appending new metadata to df_summary ... ")
    # update the summary dataframe
    updated_df_summary = update_summary.append_df_summary(df_summary, new_keys)
    print("Saving summary csv file ... \n")
    # save summary to csv 
    utils.df_to_csv(updated_df_summary, summary_filepath)

def sample_filter(filtered_filepath, summary_filepath=utils.DEFAULT_SUMMARY_FILEPATH, 
                  config=False, **kwargs):
    """ 
        Filters the sample summary csv file 

        Parameters:
            summary_filepath (str): input path to location of summary csv  

            filtered_filepath (str): output path to location of filtered 
            summary csv  

            config (str): path to location of config json file

            **kwargs: 0 or more optional arguments. Names must match a 
            column name in btb_wgs_samples.csv. If column is of type 
            'categorical' or 'object', vales must be of type 'list' 
            ispecifying a set of values to match against the argument 
            name's column in btb_wgs_samples.csv. For example, 
            'sample_name=["AFT-61-03769-21", "20-0620719"]' will include 
            just these two samples. If column is of type 'int' or 'float',
            values must be of type 'tuple' and of length 2, specifying a 
            min and max value for that column. 

        Returns:
            df_filtered (pandas DataFrame object): a dataframe of 'Pass'
            only samples filtered according to criteria set out in 
            arguments.
    """
    if config:
        error_keys = [key for key, val in kwargs.items() if val]
        # if any arguments provided with --config
        if any(error_keys):
            raise ValueError(f"arguments '{', '.join(error_keys)}' are incompatible with "
                              "the 'config' argument")
        # parse config file
        with open(config) as f:
            filter_args = json.load(f)
    else:
        # remove unused filtering args
        filter_args = {k: v for k, v in kwargs.items() if v is not None}
    print("\nfilter_samples\n")
    print("Filtering samples ... \n")
    # filter samples
    df_filtered = filter_samples.get_samples_df(summary_filepath, **filter_args)
    print("Saving filtered samples csv ... \n")
    # save filtered_df to csv
    utils.df_to_csv(df_filtered, filtered_filepath)
    return df_filtered

def phylo(results_path, consensus_path, download_only=False, n_threads=1, 
          build_tree=False, filtered_filepath=None, df_filtered=None):
    """
        Runs phylogeny on filtered samples: Downloads consensus files, 
        concatonates into 1 large fasta file, runs snp-sites, runs snp-dists
        and runs megacc 

        Pramaters:
            results_path (str):  output path to results directory

            consenus_path (str):  output path to directory for saving consensus files

            download_only (bool): only download consensus (do not run phylogeny)

            n_threads (int): number of threads for snp-dists

            build_tree (bool): build a phylogentic tree with megacc

            filtered_filepath (str): optional input path to filtered samples csv

            filtered_df (pandas DataFrame object): optional dataframe containing 
            metadata for filtered samples
    """
    # if filtered_filepath provided: load csv
    if filtered_filepath:
        df_filtered = utils.summary_csv_to_df(filtered_filepath)
    # otherwise should be a pandas DataFrame
    elif df_filtered is not None:
        pass
    else:
        raise ValueError("An argument must be provided for either filtered_filepath "
                         "or filtered_df")
    # output paths
    multi_fasta_path = path.join(results_path, "multi_fasta.fas")
    snp_sites_outpath = path.join(results_path, "snps.fas")
    snp_dists_outpath = path.join(results_path, "snp_matrix.tab")
    tree_path = path.join(results_path, "mega")
    print("\nphylogeny\n")
    # concatonate fasta files
    phylogeny.build_multi_fasta(multi_fasta_path, df_filtered, consensus_path) 
    if not download_only:
        # run snp-sites
        print("Running snp_sites ... \n")
        phylogeny.snp_sites(snp_sites_outpath, multi_fasta_path)
        # run snp-dists
        print("Running snp_dists ... ")
        phylogeny.build_snp_matrix(snp_dists_outpath, snp_sites_outpath, n_threads)
        if build_tree:
            # build tree
            print("\nRunning mega ... ")
            phylogeny.build_tree(tree_path, snp_sites_outpath)

def update_and_filter(filtered_filepath, summary_filepath=utils.DEFAULT_SUMMARY_FILEPATH, 
                      **kwargs):
    """
        Updates local copy of sample summary csv, filters samples
        and saved the output filtered csv
    """
    # update full sample summary
    update_samples(summary_filepath)
    # filter samples
    return sample_filter(filtered_filepath, summary_filepath, **kwargs)

def filter_and_phylo(results_path, consensus_path, summary_filepath=utils.DEFAULT_SUMMARY_FILEPATH, 
                     n_threads=1, build_tree=False, download_only=False, **kwargs):
    """
        Filters samples and runs phylogeny 
    """
    # filter samples
    filtered_filepath = path.join(results_path, "filtered_samples.csv")
    df_filtered = sample_filter(summary_filepath, filtered_filepath, **kwargs)
    # run phylogeny
    phylo(results_path, consensus_path, download_only, n_threads, build_tree, 
          df_filtered=df_filtered)

def full_pipeline(results_path, consensus_path, 
                  summary_filepath=utils.DEFAULT_SUMMARY_FILEPATH, n_threads=1,
                  build_tree=False, download_only=False, **kwargs):
    """
        Updates local copy of summary csv file, filters samples and
        runs phylogeny 
    """
    filtered_filepath = path.join(results_path, "filtered_samples.csv")
    # update full sample summary and filter samples
    df_filtered = update_and_filter(filtered_filepath, summary_filepath, **kwargs)
    # run phylogeny
    phylo(results_path, consensus_path, download_only, n_threads, build_tree, 
          df_filtered=df_filtered)

def main():
    parser = argparse.ArgumentParser(prog="btb-phylo")
    subparsers = parser.add_subparsers(help='sub-command help')

    # update complete summary csv
    subparser = subparsers.add_parser('update_samples', 
                                      help='updates a local copy of all sample metadata .csv file')
    subparser.add_argument("--summary_filepath", help="path to sample metadata .csv file", 
                           default=utils.DEFAULT_SUMMARY_FILEPATH)
    subparser.set_defaults(func=update_samples)

    # filter samples
    subparser = subparsers.add_parser('filter', help='filters sample metadata .csv file')
    subparser.add_argument("filtered_filepath", help="path to output filtered sample metadata .csv file")
    subparser.add_argument("--summary_filepath", help="path to sample metadata .csv file", 
                           default=utils.DEFAULT_SUMMARY_FILEPATH)
    subparser.add_argument("--config", default=None, help="path to configuration file")
    subparser.add_argument("--sample_name", "-s", dest="Sample", nargs="+", help="optional filter")
    subparser.add_argument("--clade", "-c", dest="group", nargs="+", help="optional filter")
    subparser.add_argument("--pcmapped", "-pc", dest="pcMapped", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--genomecov", "-gc", dest="GenomeCov", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--n_count", "-nc", dest="Ncount", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--flag", "-f", dest="flag", nargs="+", help="optional filter")
    subparser.add_argument("--meandepth", "-md", dest="MeanDepth", type=float, nargs=2, help="optional filter")
    subparser.set_defaults(func=sample_filter)

    # run phylogeny
    subparser = subparsers.add_parser('phylo', help='performs phylogeny')
    subparser.add_argument("results_path", help="path to results directory")
    subparser.add_argument("consensus_path", help="path to where consensus files will be held")
    subparser.add_argument("filtered_filepath", help="path to filtered sample metadata .csv file") 
    subparser.add_argument("--download_only", help="if only dowloading connsensus sequences",
                           action="store_true", default=False)
    subparser.add_argument("--n_threads", "-j", default=1, help="number of threads for snp-dists")
    subparser.add_argument("--build_tree", action="store_true", default=False, help="build a tree")
    subparser.set_defaults(func=phylo)

    # update and filter
    subparser = subparsers.add_parser('update_and_filter', 
                                      help='updates a metadata .csv file and filters samples')
    subparser.add_argument("filtered_filepath", help="path to output filtered sample metadata .csv file")
    subparser.add_argument("--summary_filepath", help="path to sample metadata .csv file", 
                           default=utils.DEFAULT_SUMMARY_FILEPATH)
    subparser.add_argument("--config", default=None, help="path to configuration file")
    subparser.add_argument("--sample_name", "-s", dest="Sample", nargs="+", help="optional filter")
    subparser.add_argument("--clade", "-c", dest="group", nargs="+", help="optional filter")
    subparser.add_argument("--pcmapped", "-pc", dest="pcMapped", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--genomecov", "-gc", dest="GenomeCov", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--n_count", "-nc", dest="Ncount", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--flag", "-f", dest="flag", nargs="+", help="optional filter")
    subparser.add_argument("--meandepth", "-md", dest="MeanDepth", type=float, nargs=2, help="optional filter")
    subparser.set_defaults(func=update_and_filter)

    # filter and phylo
    subparser = subparsers.add_parser('filter_and_phylo', help='filters samples and performs phylogeny')
    subparser.add_argument("results_path", help="path to results directory")
    subparser.add_argument("consensus_path", help="path to where consensus files will be held")
    subparser.add_argument("--summary_filepath", help="path to sample metadata .csv file", 
                           default=utils.DEFAULT_SUMMARY_FILEPATH)
    subparser.add_argument("--download_only", help="if only dowloading connsensus sequences",
                           action="store_true", default=False)
    subparser.add_argument("--n_threads", "-j", default=1, help="number of threads for snp-dists")
    subparser.add_argument("--build_tree", action="store_true", default=False, help="build a tree")
    subparser.add_argument("--config", default=None, help="path to configuration file")
    subparser.add_argument("--sample_name", "-s", dest="Sample", nargs="+", help="optional filter")
    subparser.add_argument("--clade", "-c", dest="group", nargs="+", help="optional filter")
    subparser.add_argument("--pcmapped", "-pc", dest="pcMapped", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--genomecov", "-gc", dest="GenomeCov", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--n_count", "-nc", dest="Ncount", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--flag", "-f", dest="flag", nargs="+", help="optional filter")
    subparser.add_argument("--meandepth", "-md", dest="MeanDepth", type=float, nargs=2, help="optional filter")
    subparser.set_defaults(func=filter_and_phylo)

    # full pipeline
    subparser = subparsers.add_parser('full_pipeline', 
                                      help="runs the full phylogeny pipeline: updates full \
                                            samples summary, filters samples and performs phylogeny")
    subparser.add_argument("results_path", help="path to results directory")
    subparser.add_argument("consensus_path", help = "path to where consensus files will be held")
    subparser.add_argument("--summary_filepath", help="path to sample metadata .csv file", 
                           default=utils.DEFAULT_SUMMARY_FILEPATH)
    subparser.add_argument("--download_only", help="if only dowloading connsensus sequences",
                           action="store_true", default=False)
    subparser.add_argument("--n_threads", "-j", default=1, help="number of threads for snp-dists")
    subparser.add_argument("--build_tree", action="store_true", default=False, help="build a tree")
    subparser.add_argument("--config", default=None, help="path to configuration file")
    subparser.add_argument("--sample_name", "-s", dest="Sample", nargs="+", help="optional filter")
    subparser.add_argument("--clade", "-c", dest="group", nargs="+", help="optional filter")
    subparser.add_argument("--pcmapped", "-pc", dest="pcMapped", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--genomecov", "-gc", dest="GenomeCov", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--n_count", "-nc", dest="Ncount", type=float, nargs=2, help="optional filter")
    subparser.add_argument("--flag", "-f", dest="flag", nargs="+", help="optional filter")
    subparser.add_argument("--meandepth", "-md", dest="MeanDepth", type=float, nargs=2, help="optional filter")
    subparser.set_defaults(func=full_pipeline)

    # pasre args
    kwargs = vars(parser.parse_args())
    if not kwargs:
       parser.print_help()
       return
    # retrieve opperation
    func = kwargs.pop("func")
    # run
    func(**kwargs)

if __name__ == "__main__":
    main() 
