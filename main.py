import re
from keybert import KeyBERT

import requests
import random
from pywsd.similarity import max_similarity
from pywsd.lesk import adapted_lesk
from nltk.corpus import wordnet as wn



def ans(data):
    from summarizer import Summarizer
    full_text = data
    model = Summarizer()
    result = model(full_text, min_length=60, max_length=500, ratio=0.4)
    summarized_text = ''.join(result)
    # print(summarized_text)

    bert = KeyBERT()

    def keybert_extractor(text):
        keywords = bert.extract_keywords(text, stop_words="english", top_n=15)
        results = []
        for scored_keywords in keywords:
            for keyword in scored_keywords:
                if isinstance(keyword, str):
                    results.append(keyword)
        return results

    key_words = keybert_extractor(summarized_text)
    # print (key_words)

    from nltk.tokenize import sent_tokenize
    from flashtext import KeywordProcessor
    def tokenize_sentences(text):
        sentences = [sent_tokenize(text)]
        sentences = [y for x in sentences for y in x]
        sentences = [sentence.strip() for sentence in sentences if len(sentence) > 20]
        return sentences

    def get_sentences_for_keyword(keywords, sentences):

        keyword_processor = KeywordProcessor()
        keyword_sentences = {}
        for word in keywords:
            keyword_sentences[word] = []
            keyword_processor.add_keyword(word)
        for sentence in sentences:
            keywords_found = keyword_processor.extract_keywords(sentence)
            for key in keywords_found:
                keyword_sentences[key].append(sentence)
        for key in keyword_sentences.keys():
            values = keyword_sentences[key]
            values = sorted(values, key=len, reverse=True)
            keyword_sentences[key] = values

        return keyword_sentences

    sentences = tokenize_sentences(summarized_text)
    keyword_sentence_mapping = get_sentences_for_keyword(key_words, sentences)

    # print (keyword_sentence_mapping)

    # Distractors from Wordnet
    def get_distractors_wordnet(syn, word):
        distractors = []
        word = word.lower()
        orig_word = word
        if len(word.split()) > 0:
            word = word.replace(" ", "_")
        hypernym = syn.hypernyms()
        if len(hypernym) == 0:
            return distractors
        for item in hypernym[0].hyponyms():
            name = item.lemmas()[0].name()
            # print ("name ",name, " word",orig_word)
            if name == orig_word:
                continue
            name = name.replace("_", " ")
            name = " ".join(w.capitalize() for w in name.split())
            if name is not None and name not in distractors:
                distractors.append(name)
        return distractors

    def get_wordsense(sent, word):
        word = word.lower()

        if len(word.split()) > 0:
            word = word.replace(" ", "_")

        synsets = wn.synsets(word, 'n')
        if synsets:
            wup = max_similarity(sent, word, 'wup', pos='n')
            adapted_lesk_output = adapted_lesk(sent, word, pos='n')
            lowest_index = min(synsets.index(wup), synsets.index(adapted_lesk_output))
            return synsets[lowest_index]
        else:
            return None

    # Distractors from http://conceptnet.io/
    def get_distractors_conceptnet(word):
        word = word.lower()
        original_word = word
        if (len(word.split()) > 0):
            word = word.replace(" ", "_")
        distractor_list = []
        url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/PartOf&start=/c/en/%s&limit=5" % (word, word)
        obj = requests.get(url).json()

        for edge in obj['edges']:
            link = edge['end']['term']

            url2 = "http://api.conceptnet.io/query?node=%s&rel=/r/PartOf&end=%s&limit=10" % (link, link)
            obj2 = requests.get(url2).json()
            for edge in obj2['edges']:
                word2 = edge['start']['label']
                if word2 not in distractor_list and original_word.lower() not in word2.lower():
                    distractor_list.append(word2)

        return distractor_list

    key_distractor_list = {}
    answers = []
    for keyword in keyword_sentence_mapping:
        wordsense = get_wordsense(keyword_sentence_mapping[keyword][0], keyword)
        if wordsense:
            distractors = get_distractors_wordnet(wordsense, keyword)
            if len(distractors) == 0:
                distractors = get_distractors_conceptnet(keyword)
            if len(distractors) != 0:
                key_distractor_list[keyword] = distractors
                answers.append(keyword)
        else:
            distractors = get_distractors_conceptnet(keyword)
            if len(distractors) != 0:
                key_distractor_list[keyword] = distractors
                answers.append(keyword)
    questions = []
    options = []
    index = 1
    data = ""
    ans = []
    for each in key_distractor_list:
        sentence = keyword_sentence_mapping[each][0]
        pattern = re.compile(each, re.IGNORECASE)
        output = pattern.sub(" _______ ", sentence)
        questions.append((str(index) + '.' + output))
        choices = [each.capitalize()] + key_distractor_list[each]
        top4choices = choices[:4]
        random.shuffle(top4choices)
        ans.append(top4choices)
        optionchoices = ['a', 'b', 'c', 'd']
        data += questions[index-1]+'\n'
        list = []
        for idx, choice in enumerate(top4choices):
            x = optionchoices[idx]+ ")"+ " "+ choice
            list.append(x)
        options.append(list)
        index = index + 1

    ans_pos = []
    for i in range(len(answers)):
        ans_pos.append(ans[i].index(answers[i].capitalize()) + 1)
    return questions, options, ans_pos








