import math

import nltk
import spacy
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from document import Document
from urllib.parse import urlparse
import re
import nltk



class Parse:
    # todo:
    # 1. funtion to fix all the capital and non capital words in the cursor
    # 2. add the 2 new parsing methods
    # 3. tests

    def __init__(self):
        self.asci_code_to_remove={33:None,34:None,36:None, 38:None,39:None,40:None,41:None,42:None,43:None,44:None,45:" ",46:None,58:None,59:None,60:None,61:None,62:None,63:None,91:None,92:None,93:None,94:None,96:None,123:None,124:None,125:None,126:None}
        self.stop_words = {k.lower(): "" for k in stopwords.words('english')}
        self.suspucious_words_for_entites = {}  # dictionary of suspicious words for entites, key is the term and value is the nubmer of apperances
        self.word_set = {}
        self.tweets_with_terms_to_fix = {}
      #  self.countries_codes = pd.read_csv("countries_codes").to_dict(orient='list')
        #self.nlp = spacy.load("en_core_web_sm")
        self.curr_idx = -1

    def deEmojify(self, text):
        emoji_pattern = re.compile("["
       u"\U0001F600-\U0001F64F"  # emoticons
       u"\U0001F300-\U0001F5FF"  # symbols & pictographs
       u"\U0001F680-\U0001F6FF"  # transport & map symbols
       u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
       u"\U00002500-\U00002BEF"  # chinese char
       u"\U00002702-\U000027B0"
       u"\U00002702-\U000027B0"
       u"\U000024C2-\U0001F251"
       u"\U0001f926-\U0001f937"
       u"\U00010000-\U0010ffff"
       u"\u2640-\u2642"
       u"\u2600-\u2B55"
       u"\u200d"
       u"\u23cf"
       u"\u23e9"
       u"\u231a"
       u"\ufe0f"  # dingbats
       u"\u3030"
       "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def parse_sentence(self, text):
        """
        This function tokenize, remove stop words and apply lower case for every word within the text
        :param text:
        :return:
        """

        text_tokens = word_tokenize(text)
        text_tokens_without_stopwords = [w.lower() for w in text_tokens if w not in self.stop_words]
        return text_tokens_without_stopwords

    def parse_doc(self, doc_as_list):
        """
        This function takes a tweet document as list and break it into different fields
        :param doc_as_list: list re-preseting the tweet.
        :return: Document object with corresponding fields.
        """

        tweet_id = doc_as_list[0]
        tweet_date = doc_as_list[1]
        full_text = doc_as_list[2]
        terms_list = self.parse_all_text(
            full_text, self.curr_idx)  # parse text with our functions, need to parse this one or retweet text?
        full_text = ' '.join(terms_list)
        url = doc_as_list[3]
        #url = self.parse_URL(url)
        #indices = doc_as_list[4]
        #retweet_text = doc_as_list[5]
        #retweet_text=self.parse_all_text(
         #   retweet_text, self.curr_idx)
        #retweet_url = doc_as_list[6]
        #retweet_url = self.parse_URL(url)
        retweet_indices = doc_as_list[7]
        #quote_text = doc_as_list[8]
        #quote_url = doc_as_list[9]

        term_dict = {}
        #tokenized_text = self.parse_sentence(full_text)
        doc_length = len(terms_list)  # after text operations.

        for term in terms_list:
            term = term.lower()
            if term not in term_dict.keys():
                term_dict[term] = 1
            else:
                term_dict[term] += 1

        #document = Document(tweet_id, tweet_date, full_text, url,
         #                    term_dict, doc_length)

        return [tweet_id, tweet_date, full_text, url,
                             term_dict, doc_length]

    # returns a list of all the terms in the URL divided by /, = and .

    def parse_all_text(self, text, doc_idx):
        if text is None:
            return text
        text = text.encode('ascii', 'replace').decode()
        text = text.replace("/n", "")
        text = text.translate(self.asci_code_to_remove)
        copy_text = text.split()
        # 35 <= ord(w[0]) <= 122
        copy_text = [w for w in copy_text if w[0] != '\/' and w.lower() not in self.stop_words.keys()]
        count = 0
        for word in copy_text:
            #if word[0] == '#':
             #   copy_text[count] = self.parse_hashtag(word)

            if '%' in word or 'percent' in word.lower():
                copy_text[count] = self.parse_precentage(word)

            elif word[0].isnumeric(): # if found number check next word
                word = word.replace(",", "") # 1,000 to 1000
                try: #check if its only number
                    num = float(word)
                except ValueError:
                    continue
                if num >= 1000:
                    copy_text[count] = self.parse_clean_number(num)

                elif count < len(copy_text) - 1:
                    next_word = copy_text[count+1]
                    if next_word == "Thousand" or next_word == "Million" or next_word == "Billion" or next_word == "million" or next_word == "billion" or next_word == "thousand":
                        copy_text[count + 1] = self.parse_big_number(next_word)

            elif word == "Thousand" or word == "Million" or word == "Billion" or word == "million" or word == "billion" or word == "thousand":
                copy_text[count] = self.parse_big_number(word)

            #elif word in self.countries_codes["Code"]:
             #   index = self.countries_codes["Code"].index(word)
              #  copy_text[count] = self.countries_codes["Name"][index].upper()

            elif word.isalpha() and '@' not in word and '#' not in word and '/' not in word and '.' not in word and ':' not in word and ',' not in word:
                if word.islower():
                    if word not in self.word_set.keys():
                        self.word_set[word] = None

                elif word[0].isupper():
                    if word.lower() in self.word_set.keys():
                        copy_text[count] = word.lower()
                    else:
                        self.add_word_to_future_change(doc_idx, word)
            count += 1

        return copy_text

    def parse_all_text2(self, text, idx):
        if text is None:
            return text
        text = text.encode('ascii', 'replace').decode()
        text = text.replace("/n","")
        text=text.translate(self.asci_code_to_remove)

        #text.replace("/n", "").replace("-", "").replace(",", "").replace(".","").replace(":","").replace("!","")\
        #.replace('"','').replace("&","").replace("(","").replace(")","").replace("*","").replace("+","")\
        #.replace(";","").replace(">"," ").replace("<","").replace("?","")
        #text = self.deEmojify(text)
        copy_text = text.split()

        num_flag = False
        temp_num = ""
        #self.parse_Entities(text)  # need to pass self?
        count = 0
        # 35 <= ord(w[0]) <= 122 and
        copy_text = [w for w in copy_text if w.lower() not in self.stop_words and not w[0] == "\/"]
        copy_text = self.check_word_lowercase(copy_text, idx)
        for word in copy_text:
            if (num_flag):  # if found number on previous iteration
                if word == "Thousand" or word == "Million" or word == "Billion" or word == "million" or word == "billion" or word == "thousand":
                    copy_text.remove(word)
                    copy_text[count - 1] = self.parse_big_number(temp_num + word)
                    # copy_text.replace(word,"")
                    # copy_text.replace(temp_num,self.parse_big_number(temp_num+word))
                else:
                    copy_text[count - 1] = self.parse_clean_number(temp_num)
                num_flag = False

            elif num_flag == False and (
                    word == "Thousand" or word == "Million" or word == "Billion" or word == "million" or word == "billion" or word == "thousand"):
                # in case a million appeared without any number before it
                copy_text[count] = self.parse_big_number(word)
            # if hastag
            if word[0] == "#":
                copy_text[count] = self.parse_hashtag(word)

            elif word.find('%') > -1 or word.find('percent') > -1 or word.find('percentage') > -1 or word.find(
                    'Percentage') > -1 or word.find('Percent') > -1:
                copy_text[count] = self.parse_precentage(word)

            elif word in self.countries_codes["Code"]:
                index = self.countries_codes["Code"].index(word)
                copy_text[count] = self.countries_codes["Name"][index].upper()

            elif word[0].isnumeric(): # if found number check next word
                word = word.replace(",", "")
                try: #BigSmallLetters:
                    num = float(word)
                except ValueError:
                    continue
                num_flag = True
                temp_num = word
            count += 1
            if count == len(copy_text) and num_flag:
                copy_text[count - 1] = self.parse_clean_number(temp_num)
        return copy_text

    def parse_URL(self, URL):
        parsed = urlparse(URL, allow_fragments=True)
        parsed_url = []
        parsed_url.append(parsed.scheme)
        netloc = parsed.netloc
        if "www" in netloc:
            netloc = netloc.replace("www.", "")
            parsed_url.append("www")
        parsed_url.append(netloc)
        path = parsed.path
        path = re.split(', |_|-|!|\+|=|/', path)
        query = parsed.query
        query = re.split(', |_|-|!|\+|=|/', query)
        for word in path:
            if (word != ""):
                parsed_url.append(word)
        for word in query:
            if (word != ""):
                parsed_url.append(word)
        string = ' '.join(parsed_url)
        return string

    def parse_hashtag(self, text):
        idx = 0
        final_word = ''
        list_to_add = []
        temp_txt = text
        # if "_" in temp_txt:
        temp_txt = temp_txt.replace("_", "")
        temp_txt = temp_txt.lower()
        list_to_add.append(temp_txt)
        list_with_numbers = re.split('(\d+)', text)
        if "" in list_with_numbers:
            list_with_numbers.remove("")
        parseList = []
        for item in list_with_numbers:
            if item.isnumeric() == False:
                parseList.append(item)
            else:
                list_to_add.append(item)
        for word in parseList:
            idx += 1
            temp = word
            if temp != "#":
                final_word += temp[1:]
                final_word = final_word.replace("_", " ")
                final_word = final_word.replace("-", "")
                all_capital = self.check_capital(text)
                if not all_capital:
                    final_word = re.sub(r"([A-Z])", r" \1", final_word)
                # final_word=final_word.replace(' ','')
                final_word_as_lst = str.split(final_word, " ") + list_to_add
                if (len(parseList) == idx):
                    parseList = parseList[:len(parseList) - 1] + final_word_as_lst
                else:
                    parseList = parseList[:idx] + final_word_as_lst + parseList[idx:]
        if "" in parseList:
            parseList.remove("")
        string = ' '.join(parseList)
        string_lower = string.lower()  # turn to lower case
        return string_lower

    def parse_precentage(self, text):
        return text.replace("percentage", "%").replace("percent", "%").replace(" ", "")

    def parse_clean_number(self, text):
        millfullnames = ["Thousand", "Million", "Billion", "million", "billion", "thousand"]
        if text in millfullnames:
            return text

        millnames = ['', 'K', 'M', 'B']
        n = float(text)
        # print(n)
        try:
            millidx = max(0, min(len(millnames) - 1,
                             int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))
        except:
            return str(n)

        mylist = '{:2.3f}{}'.format(n / 10 ** (3 * millidx), millnames[millidx])

        return mylist

    def parse_big_number(self, text):
        text = text.replace(",", "")

        return text.replace('Thousand', 'K').replace('Million', 'M').replace('Billion', 'B').replace('thousand',
                                                                                                     'K').replace(
            'billion', 'B').replace('million', 'M')

    def parse_Entities(self, text):
        doc = self.nlp(text)
        for entity in doc.ents:
            if entity.label_ is not "DATE" and entity.label_ is not "CARDINAL" and entity.label_ is not "QUANTITY" and "@" not in str(entity):
                if str(entity) in self.suspucious_words_for_entites.keys():
                    self.suspucious_words_for_entites[str(entity)] += text.count(str(entity))
                else:
                    self.suspucious_words_for_entites[str(entity)] = text.count(str(entity))

    def check_word_lowercase(self, words_list, idx):
        if words_list is None:
            return words_list
        count = 0
        for word in words_list:
            #word = re.sub('[0-9\[\]/"{},.:-]+', '', word)
            if not word.isalpha() or "#" in word:
                count+=1
                continue

            if word.islower():
                if word not in self.word_set.keys():
                    self.word_set[word]=None

            elif word[0].isupper():
                if word.lower() in self.word_set.keys():
                    words_list[count] = word.lower()
                else:
                    self.add_word_to_future_change(idx, word)
            count+=1

        return words_list

    def check_capital(self, text):
        if "#" in text:
            text = text.replace("#", "")
        for letter in text:
            if (letter.isnumeric() == False and letter.isupper() == False):
                return False
        return True

    def add_word_to_future_change(self, idx, word):
        if word is None or not word.isalpha():
            return
        if idx not in self.tweets_with_terms_to_fix.keys():  # new tweet
            self.tweets_with_terms_to_fix[idx] = set()
            self.tweets_with_terms_to_fix[idx].add(word)

        elif word not in self.tweets_with_terms_to_fix[idx]:  # old tweet, new word
            self.tweets_with_terms_to_fix[idx].add(word)

    def fix_word_with_future_change(self, idx, text):
        if text is None:
            return text
        for word in self.tweets_with_terms_to_fix[idx]:
            if word.lower() in self.word_set:
                text = text.replace(word, word.lower())
            else:
                text = text.replace(word, word.upper())
        return text

