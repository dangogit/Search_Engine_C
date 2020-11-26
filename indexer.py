import time
import traceback
from datetime import datetime
import pandas as pd
import json
import collections
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np


class Indexer:

    def __init__(self, config):
        #new_dictonaries
        self.inverted_idx_dicts_list = [{}, {}, {}, {}, {}, {}]
        self.inverted_idx_files_list = ["inverted_idx_a_to_c.parquet", "inverted_idx_d_to_h.parquet", "inverted_idx_i_to_o.parquet",
                                   "inverted_idx_p_to_r.parquet", "inverted_idx_s_to_z.parquet", "inverted_idx_hashtags.parquet"]
        self.posting_dicts_list = [{}, {}, {}, {}, {}, {}]
        self.posting_files_list = ["posting_file_a_to_c.parquet", "posting_file_d_to_h.parquet", "posting_file_i_to_o.parquet",
                                   "posting_file_p_to_r.parquet", "posting_file_s_to_z.parquet", "posting_file_hashtags.parquet"]
        self.config = config
        self.key = 0
        self.curr = 0
        self.term_index = 0
        self.updated_terms = {}

    def add_new_doc(self, document, doc_idx,):
        """
        This function perform indexing process for a document object.
        Saved information is captures via two dictionaries ('inverted index' and 'posting')
        :param document: a document need to be indexed.
        :return: -
        """
        document_dictionary = document[4]
        unique_terms_in_doc = self.count_unique(document_dictionary)
        # Go over each term in the doc
        for term in document_dictionary.keys():
            try:
                if not term.isalpha():
                    continue
                # freq of term in all corpus until now
                freq_in_doc = document_dictionary[term]

                self.insert_term_to_inv_idx_and_post_dict(term, freq_in_doc, doc_idx, unique_terms_in_doc, document)

            except:
                print('problem with the following key {}'.format(term))
                traceback.print_exc()

            self.curr += 1

            if self.curr==1000000:
                self.update_posting_file() #this function updates and sorts the dictionries
                #self.update_inverted_idx_files(document_dictionary,doc_idx)
                self.curr = 0

    def insert_term_to_inv_idx_and_post_dict(self, term, freq_in_doc, doc_idx,
                                             unique_terms_in_doc, document):
        index = 0
        if 'a' <= term[0] <= 'c':
            index = 0
        elif 'd' <= term[0] <= 'h':
            index = 1
        elif 'i' <= term[0] <= 'o':
            index = 2
        elif 'p' <= term[0] <= 'r':
            index = 3
        elif 's' <= term[0] <= 'z':
            index = 4
        elif term[0] == "#":
            index = 5

        inverted_idx = self.inverted_idx_dicts_list[index]
        posting_dict = self.posting_dicts_list[index]

        self.inverted_idx_dicts_list[index], self.posting_dicts_list[index] = self.update_inverted_idx_and_posting_dict(term, inverted_idx, posting_dict, freq_in_doc, doc_idx, document, unique_terms_in_doc)

    def update_inverted_idx_and_posting_dict(self, term, inverted_idx, posting_dict, freq_in_doc, doc_idx, document, unique_terms_in_doc):
        if term in inverted_idx.keys():
            number_of_docs = inverted_idx[term][0] + 1
            freq_in_corpus = inverted_idx[term][1] + freq_in_doc
            docs_list = inverted_idx[term][2]
            last_doc_idx = inverted_idx[term][3]
        else:
            number_of_docs = 1
            freq_in_corpus = freq_in_doc
            docs_list = np.array([0,0])
            last_doc_idx = doc_idx

        new_item = np.array([doc_idx, freq_in_doc])
        new_docs_list = np.vstack((docs_list, new_item))

        inverted_idx[term] = np.array([number_of_docs, freq_in_corpus, np.array([self.differnce_method(new_docs_list, last_doc_idx)]), doc_idx])
        key = term + " " + str(doc_idx)
        #posting_dict[key] = [freq_in_doc, self.index_term_in_text(term, document[2]), document[5], unique_terms_in_doc]

        return inverted_idx, posting_dict

    # list of tuples(doc_num, number of apperances in doc)
    def differnce_method(self, thelist, last_doc_index):
        i = len(thelist) -1
        if i != 0:
            new_value = thelist[i,0] - last_doc_index
            thelist[i] = [new_value, thelist[i,1]]
        return thelist

    def index_term_in_text(self, term, text):
        indexes = []
        count = 0
        spllited_text = text.split()
        for word in spllited_text:
            if word.lower() == term:
                indexes.append(count)
            count += 1
        return indexes

    def count_unique(self, document_dictionary):
        count = 0
        for term in document_dictionary:
            if document_dictionary[term] == 1:
                count += 1
        return count

    def sort_dictionarys(self, dictionary):
        return {k: dictionary[k] for k in sorted(dictionary, key=self.create_tuple_from_string)}

    def create_tuple_from_string(self, string):
        res = tuple(map(str, string.split(' ')))
        new_value = int(res[1])
        new_tuple = [res[0], new_value]
        return new_tuple

    def merge_inverted_idx_dicts(self, inverted_idx_from_file, inverted_idx_dict):
        for term in inverted_idx_dict.keys():
            if term in inverted_idx_from_file.keys():
                number_of_docs = inverted_idx_from_file[term][0] + inverted_idx_dict[term][0]
                freq_in_corpus = inverted_idx_from_file[term][1] + inverted_idx_dict[term][1]
                docs_list_from_file = inverted_idx_from_file[term][2]
                docs_list_from_local = inverted_idx_dict[term][2]
                last_doc_idx_from_file = inverted_idx_from_file[term][3]
                docs_list_from_file.append(docs_list_from_local[0])
                docs_list_from_file=self.differnce_method(docs_list_from_file, last_doc_idx_from_file)
                docs_list_from_file.append(docs_list_from_local[1:])
                last_doc_idx_from_local = inverted_idx_dict[term][3]


                inverted_idx_from_file[term] = (number_of_docs, freq_in_corpus, docs_list_from_file, last_doc_idx_from_local)
            else:
                inverted_idx_from_file[term] = inverted_idx_dict[term]

        return inverted_idx_from_file

    def update_posting_file(self):
        #'term_index' , 'doc#', 'freq', 'location_list', 'n', 'unique num of words'
        print("[" + str(datetime.now()) + "] " + "updating inverted files:")
        fmt = '%Y-%m-%d %H:%M:%S'
        d1 = datetime.strptime(datetime.now().strftime(fmt), fmt)
        d1_ts = time.mktime(d1.timetuple())

        #sort all dictionaries here
        for i in range(len(self.inverted_idx_dicts_list)):
            self.inverted_idx_dicts_list[i] = {k: self.inverted_idx_dicts_list[i][k] for k in sorted(self.inverted_idx_dicts_list[i])}

        for i in range(len(self.inverted_idx_files_list)):
            try:

                df=pd.read_parquet(self.inverted_idx_files_list[i], engine='pyarrow')
                print("opened parquet file********************")
            except:
                #inverted_idx_from_file = {}
                df=pd.DataFrame()


            inverted_idx_to_file = self.merge_inverted_idx_dicts(df.to_dict(), self.inverted_idx_dicts_list[i])


            # to json/parquete:
            try:
                new_inv_idx_to_file_as_dict=pd.DataFrame.from_dict(inverted_idx_to_file)#convert to data frame
                new_inv_idx_to_file_as_dict.to_parquet(self.inverted_idx_files_list[i])
                #json.dump(inverted_idx_to_file, inverted_idx_file)
                inverted_idx_to_file.clear()
                #inverted_idx_from_file.clear()
                #new_inv_idx_to_file_as_dict.clear() - has no attribite clear
                del new_inv_idx_to_file_as_dict
                self.inverted_idx_dicts_list[i].clear()
            except:
                traceback.print_exc()
        d2 = datetime.strptime(datetime.now().strftime(fmt), fmt)
        d2_ts = time.mktime(d2.timetuple())
        print(str(float(d2_ts - d1_ts) / 60) + " minutes")

        print("[" + str(datetime.now()) + "] " + "updating posting files:")
        d1 = datetime.strptime(datetime.now().strftime(fmt), fmt)
        d1_ts = time.mktime(d1.timetuple())


        for i in range(len(self.posting_dicts_list)):
            self.posting_dicts_list[i] = self.sort_dictionarys(self.posting_dicts_list[i])

        for i in range(len(self.posting_files_list)):

            try:
                #df=pd.read_parquet(self.inverted_idx_files_list[i], engine='pyarrow')

                #df = pd.DataFrame(data=self.posting_dicts_list)
                #df.to_parquet(self.inverted_idx_files_list[i])
                #posting_dict_from_file = json.load(posting_file)
                posting_dict_from_file = pd.read_parquet(self.posting_files_list[i],engine="pyarrow")
            except:
                posting_dict_from_file = pd.DataFrame()


            posting_dict_to_file = {**posting_dict_from_file, **self.posting_dicts_list[i]}
            posting_dict_to_file = self.sort_dictionarys(posting_dict_to_file)

            # to json:
            try:
                new_posting_file_to_disk_as_dict = pd.DataFrame.from_dict(posting_dict_to_file)#convert to dataframe
                #json.dump(self.posting_dicts_list[i], posting_file)
                new_posting_file_to_disk_as_dict.to_parquet(self.posting_files_list[i],engine="pyarrow")
                posting_dict_to_file.clear()
                posting_dict_from_file.clear()
                #new_posting_file_to_disk_as_dict.clear()
                del new_posting_file_to_disk_as_dict
                self.posting_dicts_list[i].clear()
            except:
                traceback.print_exc()


        d2 = datetime.strptime(datetime.now().strftime(fmt), fmt)
        d2_ts = time.mktime(d2.timetuple())
        print(str(float(d2_ts-d1_ts)/60) + " minutes")







