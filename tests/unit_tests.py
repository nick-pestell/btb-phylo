import unittest
import argparse

from phylogeny_test import TestPhylogeny
from filter_samples_test import TestFilterSamples
from update_summary_test import TestUpdateSummary
from consistify_test import TestConsistify
from utils_test import TestUtils


def test_suit(test_objs):                           
    suit = unittest.TestSuite(test_objs)            
    return suit                                     
                                                    
if __name__ == "__main__":                          
    phylogeny_test = [TestPhylogeny('test_build_multi_fasta'),
                      TestPhylogeny('test_extract_s3_bucket'),
                      TestPhylogeny('test_match_s3_uri'),
                      TestPhylogeny('test_process_sample_name'),
                      TestPhylogeny('test_post_process_snps_df')]
    filter_samples_test = [TestFilterSamples('test_remove_duplicates'),
                           TestFilterSamples('test_get_indexes_to_remove'),
                           TestFilterSamples('test_filter_df'),
                           TestFilterSamples('test_filter_columns_numeric'),
                           TestFilterSamples('test_filter_columns_categorical')]
    update_summary_test = [TestUpdateSummary('test_append_df_summary'),
                           TestUpdateSummary('test_get_finalout_s3_keys'),
                           TestUpdateSummary('test_extract_s3_key')]
    consistify_test = [TestConsistify('test_consistify')]
    utils_test = [TestUtils('test_extract_submission_no')]
    runner = unittest.TextTestRunner()
    parser = argparse.ArgumentParser(description='Test code')
    module_arg = parser.add_argument('--module', '-m', nargs=1, 
                                     help="module to test: phylogeny, update_summary, filter_samples, consistify or uitls'",
                                     default=None)
    args = parser.parse_args()
    if args.module:
        if args.module[0] == 'phylogeny':
            runner.run(test_suit(phylogeny_test)) 
        elif args.module[0] == 'filter_samples':
            runner.run(test_suit(filter_samples_test)) 
        elif args.module[0] == 'update_summary':
            runner.run(test_suit(update_summary_test)) 
        elif args.module[0] == 'consistify':
            runner.run(test_suit(consistify_test)) 
        elif args.module[0] == 'utils':
            runner.run(test_suit(utils_test)) 
        else:
            raise argparse.ArgumentError(module_arg, 
                                         "Invalid argument. Please use phylogeny, update_summary, filter_samples, consistify or utils")
    else:
        unittest.main(buffer=True)