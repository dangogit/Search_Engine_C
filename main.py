import search_engine

if __name__ == '__main__':
    #search_engine.main()
    #search_engine.main(corpus_path = r'C:\Users\Daniel\Desktop\BGU\שנה ג\סמסטר ה\אחזור מידע\עבודות\Data', output_path='output', stemming=False, queries='queries.txt', num_docs_to_retrieve=10)
    print(len(search_engine.load_index()))