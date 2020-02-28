import bs4 as bs
import requests
import re
import collections
import logging
import sqlite3
import sys

class SejmScraper():
    """
    Simple scraper for sejm.gov.pl
    """

    def __init__(self, db_date, polit_id):

        self.db_date = db_date
        self.politicians_id = None
        self.db_file = 'sejm_gov_pl_db.db'
        self.polit_id = polit_id

    def get_page_html(self, url_, use_encoding=None):
        """
        Get the html page structure
        :param url_: url of the site
        :param use_encoding: encoding of the site
        :return: bs4 structure
        """

        request_site = requests.get(url_)

        if request_site.status_code == 200:

            if use_encoding:
                bs_site_content = bs.BeautifulSoup(request_site.content, 'html.parser', from_encoding=use_encoding)
            else:
                bs_site_content = bs.BeautifulSoup(request_site.content, 'html.parser')

            return bs_site_content

        else:

            raise NameError('Cannot get the site {site_name}'.format(site_name=url_))

    def get_politician_id(self):
        """
        Returns dictionary with id for each and every politician for all terms
        :return: dictionary {'1': ['1', '2', '3'], '2': [(1, 'abcd'), (2, 'efgh'),...])
        """

        def get_all_old_polit_id(term_of_office):
            """
            get the id of each and every politician in the specific term (active/non-active/elected during the term)
            unfortunately it gives us only the hash needed to enter politician 'portfolio' site
            but we are in luck, because politician id == position on the list
            *only for the terms < 6
            :param bs_site_conntent:
            :return: list of strings (i.e. [('1', '1497d6103c39c8e9c125793e00398fe1),...])
            """
            ### TODO add terms of services from the before the WW II
            rp_list = [
                       'dziesiata',
                       'pierwszaRP',
                       'drugaRP',
                       'trzeciaRP',
                       'czwartaRP',
                       'piataRP',
                       'szostaRP']

            regex_list = [
                          'nsf\/67021600f180f322c125681600312192\/(.+)\?',
                          'nsf\/90faebcb8740c764c12568160030aa2d\/(.+)\?',
                          'nsf\/ddf3b96aef405850c1256816002f8f40\/(.+)\?',
                          'nsf\/46f5c122f008a9f4c1256ada004b9696\/(.+)\?',
                          'nsf\/f37879dbe37d1bd1c1257088003d7beb\/(.+)\?',
                          'nsf\/d8c835fab6f53963c125737c002df90b\/(.+)\?',
                          'nsf\/1934403697ebc379c125793d0048a19a\/(.+)\?']

            set_pages = []

            politician_number = 1

            if term_of_office > 6:

                raise NameError('Please use parser for the new version of the goverment site')

            else:

                numer_rp = rp_list[term_of_office]
                regex_pages = regex_list[term_of_office]

            site_content = self.get_page_html('http://orka.sejm.gov.pl/ArchAll2.nsf/' +
                                              numer_rp)

            a_list = site_content.find_all('a', {'target': 'Prawa'})

            for a_poitician_id in a_list:

                _re_search = re.search(regex_pages, a_poitician_id['href'])

                if _re_search:
                    set_pages.append((politician_number, _re_search.group(1)))

                    politician_number += 1

            return set_pages

        def get_all_new_polit_id(term_of_office):
            """
            get the id of each and every politician in the specific term (active/non-active/elected during the term)
            only for the terma > 6
            :param bs_site_conntent: bs4 structure of the page
            :return: list of strings (i.e. ['458', ...])
            """

            id_numbers = []

            # A - actual politicians
            # B - non actual politicians
            # N - new politicians (elected during the current term of office)

            type_of_politician = ['A', 'B', 'N']

            for type_ in type_of_politician:

                if term_of_office > 6:

                    site_content = self.get_page_html('http://www.sejm.gov.pl/sejm' +
                                                      str(term_of_office) +
                                                      '.nsf/poslowie.xsp?type=' + type_)

                else:

                    raise NameError('Please use parser for the old version of the goverment site')

                a_href_search = '(/sejm' + str(term_of_office) + '\.nsf\/posel\.xsp\?id=)(\d+)'

                pol_links = site_content.find_all('a')

                for link in pol_links:

                    _re_search = re.search(a_href_search, link.attrs['href'])

                    if _re_search:
                        id_numbers.append(_re_search.group(2))

            return id_numbers

        def get_politician_id(terms_of_office):
            """
            :param term_of_service: list of terms of service ([1,2,3,4,5,6,7,8])
            :return: dictionary of politicians ({'1': [links to politician page], '7': [ids of poilticians])
            """

            dict_of_politians_ids = collections.defaultdict(list)

            for term in terms_of_office:

                if term > 6:
                    dict_of_politians_ids[str(term)] = get_all_new_polit_id(term)
                else:
                    dict_of_politians_ids[str(term)] = get_all_old_polit_id(term)

            return dict_of_politians_ids

        self.politicians_id = get_politician_id(range(0, 10))

        if self.politicians_id:
            return True
        else:
            raise NameError("Import of ID list failed - please retry this operation")

    def basic_information_scrap(self, get_id, term_of_service):
        """
        Get basic information about politician
        :return: dictionary with all of the politician attributes
        """

        def get_person_attribute(attributes):
            """
            iterate through all values in the list and return some values
            only for the terms < 6
            :param attribute: tr value
            :return: dictionary with most of the politician attributes
            """

            hard_values = [
                # 'Aktywność poselska',
                'Data i miejce urodzenia',
                'Data ślubowania',
                'Data wygaśnięcia mandatu',
                'Funkcja w Sejmie',
                'Komisje Sejmowe',
                'Liczba głosów',
                'Lista:',
                'Naruszenie zasad etyki poselskiej',
                'Okręg wyborczy',
                'Partia (wybory)',
                'Podkomisje',
                'Stan cywilny',
                'Staż parlamentarny',
                'Tytuł/stopień naukowy',
                'Ukończona szkoła',
                'Wykształcenie',
                'Zawód',
                'Zawód/stanowisko',
                'Znajomość języków']

            attr_dict = {}

            for i, attribute in enumerate(attributes):

                for attr_ in hard_values:

                    if attr_.lower() in attribute.lower():

                        search_ = re.search(':(.+)', attribute)

                        if search_:
                            attr_dict[attr_.lower()] = search_.group(1)

                            prev_attr = attr_.lower()

                if isinstance(attribute.lower(), str) \
                        and len(attribute.lower()) > 0 \
                        and attribute.lower()[0] == '-':
                    attr_dict[prev_attr] = attr_dict[prev_attr] + ' | ' + attribute.lower()[1:].strip()

            attr_dict['name'] = attributes[2].strip()

            # add missing columns
            for attr_ in hard_values:

                if attr_.lower() not in attr_dict.keys():
                    attr_dict[attr_.lower()] = ''

            return attr_dict

        def new_portfolio_site(get_id, term_of_office):
            """
            Portfolio for VII and VIII cadency
            :param get_id: politician id
            :return: dictionary with all attributes of the specific politician
            """

            attr_values = [
                'Funkcja w Sejmie',
                'Wybran',
                'Ukończona szkoła',
                'Tytuł/stopień naukowy',
                'Data i miejsce urodzenia',
                'Klub/koło',
                'Strona WWW',
                'Funkcja w klubie/kole',
                'Lista',
                'Staż parlamentarny',
                'Okręg wyborczy',
                'Wykształcenie',
                'Zawód',
                'Email',
                'Liczba głosów',
                'Wygaśnięcie mandatu'
            ]

            polit_person = {}

            site_content = self.get_page_html('http://www.sejm.gov.pl/sejm' +
                                              str(term_of_office) +
                                              '.nsf/posel.xsp?id=' + get_id)

            print('http://www.sejm.gov.pl/sejm' +
                  str(term_of_office) +
                  '.nsf/posel.xsp?id=' + get_id)

            li_data = site_content.find_all('li')

            li_data_get_text = [li.get_text() for li in li_data]

            for li_ in li_data_get_text:

                if ':' in li_:

                    for attr_ in attr_values:

                        if attr_.lower() in li_.lower():

                            if attr_.lower() == 'wybran':
                                dict_key_ = 'wybrano'
                            else:
                                dict_key_ = attr_.lower()

                            polit_person[dict_key_] = li_[li_.find(':') + 1:].replace('\xa0', '')

            # adding missing attributes

            for attr_ in attr_values:

                if attr_.lower() not in polit_person.keys() and attr_.lower() != 'wybran':
                    polit_person[attr_.lower()] = ''

            # add name and surname
            title_data = site_content.find_all('title')

            polit_person['name'] = title_data[0].get_text().strip()
            polit_person['get_term'] = term_of_office
            polit_person['actual_party'] = polit_person['klub/koło']

            return polit_person

        def old_portfolio_site(get_id, term_of_office):
            """
            Portfolio for terms < 6
            :param get_id: id of the specific politician
            :return: dictionary with all of the politician attributes
            """

            cadency_hash = [
                '67021600f180f322c125681600312192',
                '90faebcb8740c764c12568160030aa2d',
                'ddf3b96aef405850c1256816002f8f40',
                '46f5c122f008a9f4c1256ada004b9696',
                'f37879dbe37d1bd1c1257088003d7beb',
                'd8c835fab6f53963c125737c002df90b',
                '1934403697ebc379c125793d0048a19a']

            site_content = self.get_page_html('http://orka.sejm.gov.pl/ArchAll2.nsf/' +
                                              cadency_hash[int(term_of_office)] + '/' + get_id[1], 'ISO-8859-2')

            for br in site_content.find_all("br"):
                br.replace_with("|")

            td_data = site_content.find_all('td')

            td_data_get_text = [text_ for td in td_data for text_ in td.get_text(strip=True).split('|')]

            polit_person = get_person_attribute(td_data_get_text)

            polit_person['actual_party'] = site_content.find_all('td', {'class': 'Klub'})[0].get_text()
            polit_person['get_term'] = term_of_office

            return polit_person

        def unify_portfolio_data(portfolio_data):
            """
            Unifing data structure
            :param portfolio_data: dictionary with attributes
            :return: dictionary of attributes
            """

            unify_data = {}

            map_to_unify_old = {'name': ['name'],
                                'elected': ['data ślubowania'],
                                'graduated school': ['ukończona szkoła'],
                                'education level': ['wykształcenie'],
                                'occupation': ['zawód', 'zawód/stanowisko'],
                                'function': ['funkcja w sejmie'],
                                'academic title': ['tytuł/stopień naukowy'],
                                'date and place of birth': ['data i miejce urodzenia'],
                                'party/section': ['partia (wybory)'],
                                'website': ['None'],
                                'function in the party': ['None'],
                                'election list': ['lista'],
                                'previous cadency': ['staż parlamentarny'],
                                'constituency': ['okręg wyborczy'],
                                'email': ['None'],
                                'number of votes': ['liczba głosów'],
                                'end of cadency': ['data wygaśnięcia mandatu'],
                                'ethics violation': ['naruszenie zasad etyki poselskiej'],
                                'married status': ['stan cywilny'],
                                'languages': ['znajomość języków'],
                                'parliamentary committees': ['komisje sejmowe'],
                                'parliamentary undercommittees': ['podkomisje'],
                                'get_term': ['term_of_office'],
                                'last_party': ['actual_party']}

            map_to_unify_new = {'name': ['name'],
                                'elected': ['wybrano'],
                                'graduated school': ['Ukończona szkoła'],
                                'education level': ['wykształcenie'],
                                'occupation': ['zawód'],
                                'function': ['funkcja w sejmie'],
                                'academic title': ['tytuł/stopień naukowy'],
                                'date and place of birth': ['data i miejsce urodzenia'],
                                'party/section': ['klub/koło'],
                                'website': ['strona www'],
                                'function in the party': ['funkcja w klubie/kole'],
                                'election list': ['lista'],
                                'previous cadency': ['staż parlamentarny'],
                                'constituency': ['okręg wyborczy'],
                                'email': ['email'],
                                'number of votes': ['liczba głosów'],
                                'end of cadency': ['wygaśnięcie mandatu'],
                                'ethics violation': ['None'],
                                'married status': ['None'],
                                'languages': ['None'],
                                'parliamentary committees': ['None'],
                                'parliamentary undercommittees': ['None'],
                                'get_term': ['term_of_office'],
                                'last_party': ['actual_party']}

            if int(portfolio_data['get_term']) > 6:

                for unify_key_ in sorted(map_to_unify_new):

                    for value_ in map_to_unify_new[unify_key_]:

                        for portfolio_key_ in portfolio_data:

                            if portfolio_key_ == 'None':

                                unify_data[unify_key_] = None
                                break

                            elif value_ == portfolio_key_:

                                unify_data[unify_key_] = portfolio_data[portfolio_key_]
                                break

                            else:
                                continue

            else:

                for unify_key_ in sorted(map_to_unify_old):

                    for value_ in map_to_unify_old[unify_key_]:

                        for portfolio_key_ in portfolio_data:

                            if portfolio_key_ == 'None':

                                unify_data[unify_key_] = None
                                break

                            elif value_ == portfolio_key_:

                                unify_data[unify_key_] = portfolio_data[portfolio_key_]
                                break

                            else:
                                continue

            return unify_data

        if int(term_of_service) > 6:
            portfolio_data = unify_portfolio_data(new_portfolio_site(get_id, term_of_service))
        else:
            portfolio_data = unify_portfolio_data(old_portfolio_site(get_id, term_of_service))

        return portfolio_data

    def build_sql_values_for_basic_data(self, values_dict, term, id):
        """
        Build sql query for bio data
        :param values_dict:
        :param term:
        :param id:
        :return: sql query
        """
        if int(term) > 6:
            id = str(term) + '_' + str(id)

        input_string = '"' + str(term) + '",' + '"' + str(id) + '",'

        person_info = [
            'name',
            'elected',
            'graduated school',
            'education level',
            'occupation',
            'function',
            'academic title',
            'date and place of birth',
            'party/section',
            'website',
            'function in the party',
            'election list',
            'previous cadency',
            'constituency',
            'email',
            'number of votes',
            'end of cadency',
            'ethics violation',
            'married status',
            'languages',
            'parliamentary committees',
            'parliamentary undercommittees',
            'get_term',
            'last_party'
        ]

        for info_ in person_info:

            input_string += '"' + str(values_dict.get(info_, 'Null')).replace('"', '') + '",'

        return input_string + '"' + str(self.db_date) + '"'

    def build_sql_values_for_speech_data(self, values_dict, term, id):
        """
        Build sql query for speech data
        :param values_dict:
        :param term:
        :param id:
        :return: sql query
        """
        if int(term) > 6:
            id = str(term) + '_' + str(id)

        input_string = '"' + str(term) + '",' + '"' + str(id) + '",'

        speech_info = [
            'posiedzenie',
            'dzien',
            'data',
            'numer',
            'tytul',
            'speech_number',
            'link_to_speech',
            'wypowiedz'
        ]

        for info_ in speech_info:

            input_string += '"' + str(values_dict.get(info_, 'Null')).replace('"', '') + '",'

        return input_string + '"' + str(self.db_date) + '"'

    def build_basic_informations(self):
        """
        Download and save bio data
        :return:
        """

        connection = sqlite3.connect(self.db_file)
        cursor = connection.cursor()

        basic_informations_columns = 'term, id_, full_name, elected, graduated_school, education_level, occupation, \
        				function, academic_title, date_and_place_of_birth, party_section, website, function_in_the_party, \
        				election_list, previous_cadency, constituency, email, number_of_votes, end_of_cadency, \
        				ethics_violation, married_status, languages, parliamentary_committees, parliamentary_undercommittees, \
        				get_term, last_party, db_date'

        if not self.politicians_id:

            raise NameError('Please initialize list of all politicians with politician_init method')

        for term_ in self.politicians_id.keys():
            if term_ >= self.polit_id:
                for politician_ in self.politicians_id[term_]:

                    if int(term_) > 6:
                        sql_id = str(term_) + '_' + str(politician_)
                    else:
                        sql_id = politician_

                    check_person_id = """
                                         SELECT id_
                                         FROM {table_name}
                                         WHERE db_date = {db_date}
                                         AND term = {term}
                                         AND id_ = {id}
                                      """.format(
                                            table_name='portraits',
                                            db_date= '"' + str(self.db_date) + '"',
                                            term = '"' + str(term_) + '"',
                                            id = '"' + str(sql_id) + '"'
                                                )

                    cursor.execute(check_person_id)
                    query_results = cursor.fetchall()

                    if len(query_results) == 0:

                        basic_informations = self.basic_information_scrap(politician_, term_)

                        try:

                            cursor.execute("INSERT INTO {table_name} ({table_columns}) VALUES ({table_values})". \
                                           format(table_name='portraits', table_columns=basic_informations_columns,
                                                  table_values=self.build_sql_values_for_basic_data(basic_informations, term_, politician_)))

                            connection.commit()
                        except sqlite3.IntegrityError:
                            print('ERROR: ID already exists in PRIMARY KEY column {}'.format(self.build_sql_values_for_basic_data(basic_informations, term_, politician_)))

                        connection.commit()

        connection.close()

        return True

    def speech_scrap(self, get_id, term_of_service):

        def get_new_politician_speeches(get_id, term_of_service):
            """
            download all speeches for the specific politician
            term of office > 6
            :param politician:
            :param term:
            :return:
            """

            def get_list_of_speeches(get_id, term_of_service):

                site_content = self.get_page_html('http://www.sejm.gov.pl/sejm' +
                                                  str(term_of_service) +
                                                  '.nsf/wypowiedzi.xsp?id=' +
                                                  get_id +
                                                  '&type=A&symbol=WYPOWIEDZI_POSLA&page=1')

                set_pages = set()

                page_ids = site_content.find_all('li')

                regex_pages = '\?page=(\d)+&'

                for page_ in page_ids:

                    try:

                        _re_search = re.search(regex_pages, page_.a.get('href'))

                        if _re_search:
                            set_pages.update(_re_search.group(1))

                    except:
                        pass

                if len(set_pages) == 0:
                    set_pages.update('1')

                return set_pages

            def check_db_for_speech(term_, id_, speech_link):

                connection = sqlite3.connect(self.db_file)
                cursor = connection.cursor()

                sql_id = str(term_) + '_' + str(id_)

                check_person_id = """
                                 SELECT id_
                                 FROM {table_name}
                                 WHERE db_date = {db_date}
                                 AND term = {term}
                                 AND id_ = {id}
                                 AND speech_link = {speech_link}
                              """.format(
                    table_name='speech_data',
                    db_date='"' + str(self.db_date) + '"',
                    term='"' + str(term_) + '"',
                    id='"' + str(sql_id) + '"',
                    speech_link='"' + speech_link + '"'
                )

                cursor.execute(check_person_id)
                query_results = cursor.fetchall()

                print('checked for: ', term_, id_, speech_link)

                if len(query_results) == 0:
                    print('download')
                    result = True
                else:
                    print('pass')
                    result = False

                connection.close()
                return result

            def speech_decomposition(term_of_service, speech_link):

                site_content = self.get_page_html('http://www.sejm.gov.pl/sejm' +
                                                  term_of_service +
                                                  '.nsf/' +
                                                  speech_link)

                bs_p_list = site_content.find_all('p', {'class': ''})

                raw_text = ''

                for p in bs_p_list:
                    raw_text += p.get_text(separator='\n').strip() + ' '

                # raw_text = site_content.body.get_text(separator='\n')

                return raw_text

            def get_all_speeches(id_politican, term_of_service, set_of_sites):

                speech_list = []

                for page_id in set_of_sites:

                    site_content = self.get_page_html('http://www.sejm.gov.pl/sejm' +
                                                      str(term_of_service) +
                                                      '.nsf/wypowiedzi.xsp?id=' +
                                                      id_politican +
                                                      '&type=A&symbol=WYPOWIEDZI_POSLA&page=' +
                                                      page_id)

                    page_ids = site_content.find_all('table', {'class': 'table border-bottom lista-wyp'})

                    for table in page_ids:

                        for tr in table.find_all('tr'):

                            table_row = tr.find_all('td')

                            if len(table_row) > 1:

                                if check_db_for_speech(term_of_service, id_politican, table_row[4].a.get('href')):
                                    polit_speeches = dict()

                                    polit_speeches['politician_id'] = id_politican
                                    polit_speeches['term_of_office'] = term_of_service

                                    polit_speeches['posiedzenie'] = table_row[0].get_text()
                                    polit_speeches['dzien'] = table_row[1].get_text()
                                    polit_speeches['data'] = table_row[2].get_text()
                                    polit_speeches['numer'] = table_row[3].get_text()
                                    polit_speeches['tytul'] = table_row[4].get_text()
                                    polit_speeches['speech_number'] = re.search('wyp=(\d+)',
                                                                                table_row[4].a.get('href')).group(1)
                                    polit_speeches['link_to_speech'] = table_row[4].a.get('href')

                                    polit_speeches['wypowiedz'] = speech_decomposition(term_of_service,
                                                                                       polit_speeches['link_to_speech'])

                                    speech_list.append(polit_speeches)

                return speech_list

            list_of_speeches = get_list_of_speeches(get_id, term_of_service)


            return get_all_speeches(get_id, term_of_service, list_of_speeches)

        def get_old_politician_speeches(get_id, term_of_service):
            """
            download all speeches for the specific politician
            term of office > 6
            :param politician:
            :param term:
            :return:
            """

            def speech_decomposition(speech_link):

                site_content = self.get_page_html('http://orka2.sejm.gov.pl' +
                                                  speech_link)

                bs_p_list = site_content.find_all('p', {'class': ''})

                raw_text = ''

                for p in bs_p_list:
                    raw_text += p.get_text(separator='\n').strip().replace('\n', '\n') + ' '

                return raw_text

            def check_db_for_speech(term_, sql_id, speech_link):

                connection = sqlite3.connect(self.db_file)
                cursor = connection.cursor()

                check_person_id = """
                                 SELECT id_
                                 FROM {table_name}
                                 WHERE db_date = {db_date}
                                 AND term = {term}
                                 AND id_ = {id}
                                 AND speech_link = {speech_link}
                              """.format(
                            table_name='speech_data',
                            db_date='"' + str(self.db_date) + '"',
                            term='"' + str(term_) + '"',
                            id='"' + str(sql_id) + '"',
                            speech_link = '"' + speech_link + '"'
                        )

                cursor.execute(check_person_id)
                query_results = cursor.fetchall()

                print('checked_values: ', term_, sql_id, speech_link)

                if len(query_results) == 0:
                    print('adding')
                    result = True
                else:
                    print('ommited')
                    result = False

                connection.close()
                return result

            def get_all_speeches(id_politican, term_of_service):

                speech_list = []

                if len(str(id_politican[0])) == 1:
                    temp_politician_id = '00' + str(id_politican[0])
                elif len(str(id_politican[0])) == 2:
                    temp_politician_id = '0' + str(id_politican[0])
                else:
                    temp_politician_id = str(id_politican[0])

                site_content = self.get_page_html('http://orka2.sejm.gov.pl/Debata' +
                                                  str(term_of_service) +
                                                  '.nsf/idWWW?OpenView&RestricttoCategory=' +
                                                  temp_politician_id)

                page_tables = site_content.find_all('table')

                try:

                    for tr in page_tables[1].find_all('tr'):

                        table_row = tr.find_all('td')

                        if len(table_row) > 1:

                            if check_db_for_speech(term_of_service, id_politican, table_row[7].a.get('href')):

                                polit_speeches = dict()

                                polit_speeches['politician_id'] = temp_politician_id
                                polit_speeches['term_of_office'] = term_of_service

                                polit_speeches['posiedzenie'] = table_row[0].get_text()
                                polit_speeches['dzien'] = table_row[2].get_text()
                                polit_speeches['data'] = table_row[4].get_text()
                                polit_speeches['numer'] = table_row[6].get_text()
                                polit_speeches['tytul'] = table_row[7].get_text()
                                polit_speeches['speech_number'] = None
                                polit_speeches['link_to_speech'] = table_row[7].a.get('href')

                                polit_speeches['wypowiedz'] = speech_decomposition(polit_speeches['link_to_speech'])

                                speech_list.append(polit_speeches)
                except:

                    polit_speeches = dict()

                    polit_speeches['politician_id'] = temp_politician_id
                    polit_speeches['term_of_office'] = term_of_service

                    polit_speeches['posiedzenie'] = None
                    polit_speeches['dzien'] = None
                    polit_speeches['data'] = None
                    polit_speeches['numer'] = None
                    polit_speeches['tytul'] = None
                    polit_speeches['speech_number'] = None
                    polit_speeches['link_to_speech'] = None

                    polit_speeches['wypowiedz'] = None

                    speech_list.append(polit_speeches)

                return speech_list

            return get_all_speeches(get_id, term_of_service)

        if int(term_of_service) > 6:
            speech_data = get_new_politician_speeches(get_id, term_of_service)
        elif int(term_of_service) > 0:
            speech_data = get_old_politician_speeches(get_id, term_of_service)
        else:
            # there is no speech data for term '89-'91
            speech_data = []

        return speech_data

    def build_speech_data(self):

        connection = sqlite3.connect(self.db_file)
        cursor = connection.cursor()

        speech_columns = 'term, id_, session_number, day_, date_,number_, speech_title , speech_number , \
                speech_link, speech_raw, db_date'

        if not self.politicians_id:
            raise NameError('Please initialize list of all politicians with politician_init method')

        for term_ in self.politicians_id.keys():
            if int(term_) >=self.polit_id:
                for politician_ in sorted(self.politicians_id[term_]):
                    if int(politician_) >= 1:
                        speech_list = self.speech_scrap(politician_, term_)

                        if speech_list:

                            for speech_ in speech_list:

                                try:

                                    cursor.execute("INSERT INTO {table_name} ({table_columns}) VALUES ({table_values})". \
                                                   format(table_name='speech_data', table_columns=speech_columns,
                                                          table_values=self.build_sql_values_for_speech_data(speech_, term_,
                                                                                                             politician_)))

                                    connection.commit()
                                except sqlite3.IntegrityError:
                                    print('ERROR: ID already exists in PRIMARY KEY column {}'.format
                                          (self.build_sql_values_for_speech_data(speech_, term_, politician_)))

                                connection.commit()

        connection.close()

        return True


def main():

    # setup logging configuration
    logging.basicConfig(filename='scraper_log.log',
                        format='%(asctime)s %(name)13s %(levelname)8s: ' +
                               '%(message)s',
                        level=logging.INFO)

    logging.getLogger(__name__)

    logging.info('Sraper started')

    date_of_scrap = sys.argv[1]
    scrap_command = sys.argv[2]
    from_election = sys.argv[3]

    sejm_gov_scraper = SejmScraper(date_of_scrap, from_election)

    sejm_gov_scraper.get_politician_id()

    if scrap_command == 'build_basic_informations':
        sejm_gov_scraper.build_basic_informations()
    elif scrap_command == 'build_speech_data':
    # get all speeches
        sejm_gov_scraper.build_speech_data()
    else:
        print('Nothing to do!')

    logging.info('Done!')

    return True


if __name__ == '__main__':

    main()
