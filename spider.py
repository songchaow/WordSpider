from bs4 import BeautifulSoup
import requests
from lxml import etree
import os
import re

"""
h: word title
hm: id
pos: part of speech
sn-gs: category
    shcut: categorie name
    sn-g: each entry
        sym_first:
            *oxford3000
        gram-g:
            gram (multi)
        cf: usage pattern
        def: definition
        xr-gs:
            prefix: kinds like 'synonym'
            <a> ...
        x-gs: example sentences
            x-g:
                cf: usage pattern
                rx-g: sentence
                    x:
                        cl: collections
    sn-g: ...

dis-g 
"""


class WordNotFound(Exception):
    message = "This word is not found on OALD!"


class WordSpider:
    base_url = 'http://www.oxfordlearnersdictionaries.com/definition/english/'
    curr_xml = None
    curr_line = 0

    def write_to_file(self, fstate, fdata):
        ''' write contents to file and modify pointer '''
    @staticmethod
    def init_tree(tree):
        if(tree.find('dictionary')):
            if(tree.find('dictionary').find('content') is None):
                content = tree.new_tag('content')
                tree.find('dictionary').append(content)
        else:
            dict = tree.append(tree.new_tag('dictionary'))
            tree.find('dictionary').append(tree.new_tag('content'))

    def fetch_single_word(self, word, xml_content, response=None):
        if(WordSpider.base_url in word):
            url = word
        else:
            url = WordSpider.base_url + word
        if response is None:
            response = requests.get(url)
        if(response.status_code == 404):
            raise WordNotFound()
        else:
            word = xml_content.new_tag('word')
            xml_content.append(word)
            soup = BeautifulSoup(response.text, "lxml")
            name = xml_content.new_tag(
                'name', string=soup.find(class_='h').text)
            word.append(name)
            # add 'name' to attributes:
            word['name'] = name.text
            phonetics = soup.find(
                class_='pron-gs ei-g').find_all(class_='pron-g')
            xml_phonetics = xml_content.new_tag('phonetics')
            word.append(xml_phonetics)
            for phonetic in phonetics:

                xml_phonetic = xml_content.new_tag('phonetic')
                xml_phonetics.append(xml_phonetic)
                xml_phonetic.append(xml_content.new_tag(
                    'type', string=phonetic.find(class_='prefix').text))

                xml_phonetic.append(xml_content.new_tag('data', string=phonetic.find(
                    class_='phon').text.replace('BrE', '').replace('NAmE', '')))
            if(soup.find(class_='hm')):
                id = xml_content.new_tag(
                    'id', string=soup.find(class_='hm').text)
                word.append(id)
            partofspeech = xml_content.new_tag(
                'pos', string=soup.find(class_='pos').text)
            word.append(partofspeech)
            word['pos'] = partofspeech.text
            xml_categories = xml_content.new_tag('categories')
            word.append(xml_categories)
            categories = soup.find_all(class_='sn-gs')
            for category in categories:
                xml_category = xml_content.new_tag('category')
                xml_categories.append(xml_category)
                xml_category.append(xml_content.new_tag(
                    'name', string=category.find(class_='shcut').text))
                # fetch each entry in this category
                entries = category.find_all(class_='sn-g')
                for entry in entries:
                    xml_entry = xml_content.new_tag('entry')
                    xml_category.append(xml_entry)
                    if(entry.find(class_='sym-first')):
                        xml_entry.append(xml_content.new_tag(
                            'symbol', string=entry.find(class_='sym-first').text))
                    gram_list = xml_content.new_tag('gram_list', string=','.join(
                        [gram.text for gram in entry.find_all(class_='gram')]))
                    xml_entry.append(gram_list)
                    # add 'cf' belonging to entry
                    cf = entry.find(class_='cf')
                    if(cf.parent == entry):
                        xml_entry.append(xml_content.new_tag(
                            'usage pattern', string=cf.text))
                    xml_entry.append(xml_content.new_tag(
                        'definition', string=entry.find(class_='def').text))
                    if entry.find(class_='xr-gs'):
                        related_word = xml_content.new_tag('related_word')
                        xml_entry.append(related_word)
                        related_word.append(xml_content.new_tag(
                            'type', string=entry.find(class_='xr-gs').find(class_='prefix').text))
                        related_word.append(xml_content.new_tag('word', string=entry.find(class_='xr-gs').find('a').text))
                    xml_collections = xml_content.new_tag('collections')
                    xml_entry.append(xml_collections)
                    # add examples
                    xml_examples = xml_content.new_tag('examples')
                    xml_entry.append(xml_examples)
                    for example in entry.find_all(class_='x-g'):
                        xml_example = xml_content.new_tag('example')
                        xml_examples.append(xml_example)
                        if example.find(class_='cf'):
                            xml_example.append(xml_content.new_tag(
                                'usage pattern', string=example.find(class_='cf').text))
                        xml_example.append(xml_content.new_tag(
                            'content', string=example.find(class_='rx-g').text))
                        if example.find(class_='cl'):
                            xml_example.append(xml_content.new_tag(
                                'collection', string=example.find(class_='cl').text))
                            xml_collections.append(xml_content.new_tag(
                                'collection', string=example.find(class_='cl').text))
            # deal with idioms
            if soup.find_all(class_='idm-g'):
                xml_idioms = xml_content.new_tag('idioms')
                word.append(xml_idioms)
                idioms = soup.find_all(class_='idm-g')
                for idiom in idioms:
                    xml_idiom = xml_content.new_tag('idiom')
                    xml_idioms.append(xml_idiom)
                    xml_idiom.append(xml_content.new_tag('title',string=idiom.find(class_='idm').text))
                    xml_idiom.append(xml_content.new_tag('def',string=idiom.find(class_='sn-g').text))
                    if(idiom.find(class_='x-gs')):
                        xml_idiom.append(xml_content.new_tag('example',string=idiom.find(class_='x-g').text))
    
    def fetch_multi_words(self,word,xml_content):
        ''' fetch all words related to keyword 'word' '''
        url = WordSpider.base_url+word
        response = requests.get(url)
        if(response.status_code == 404):
            raise WordNotFound()
        else:
            soup = BeautifulSoup(response.content)
            all_matches = soup.find(class_='accordion ui-grad').find(class_='list-col').find_all('li')
            urls = []
            for word in all_matches:
                pos = word.find('pos').text
                word.find('pos').extract()
                item = word.text
                # find whether it's been fetched
                if(not xml_content.find('word',name=item,pos=pos)):
                    urls += word.find('a')['href']
            # start to fetch each entry
            self.fetch_single_word(word, xml_content, response=response)
            for url in urls:
                self.fetch_single_word(url, xml_content)

    def start(self):
        fstate = open('state.txt', 'w+')
        dict = open('dictionary.xml', 'wb+')
        line = fstate.readline()
        if(re.match('curr_line:\s*(\d+)', line)):
            # load curr_line if existing
            WordSpider.curr_line = re.match(
                'curr_line:\s*(\d+)', line).group(1)
        else:
            fstate.write('curr_line: ' + WordSpider.curr_line)
        tree = BeautifulSoup(dict, "xml")
        self.init_tree(tree)

    
