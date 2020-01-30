import random
import itertools
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from base import mods
from base.tests import BaseTestCase
from census.models import Census
from mixnet.mixcrypt import ElGamal
from mixnet.mixcrypt import MixCrypt
from mixnet.models import Auth
from voting.models import Voting, Question, QuestionOption

# Imports para selenium
""" from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
import unittest 
from selenium import webdriver
import time  """


class VotingTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.newObject = Question(desc='test')
        self.newObject.save()
        self.opt = QuestionOption(question=self.newObject, option='1', yes = True, no=False)
        self.opt.save()
        self.opt2 = QuestionOption(question=self.newObject, option='2', yes = False, no=True)
        self.opt2.save()

    def tearDown(self):
        super().tearDown()
        self.question = None
        self.questionOption = None

    def test_store_question(self):
        self.assertEqual(Question.objects.count(), 1)

    def test_store_questionOptions(self):
        self.assertEqual(QuestionOption.objects.count(), 2)

    def encrypt_msg(self, msg, v, bits=settings.KEYBITS):
        pk = v.pub_key
        p, g, y = (pk.p, pk.g, pk.y)
        k = MixCrypt(bits=bits)
        k.k = ElGamal.construct((p, g, y))
        return k.encrypt(msg)

    def create_voting(self):
        q = Question(desc='test question')
        q.save()
        for i in range(5):
            opt = QuestionOption(question=q, option='option {}'.format(i+1), yes = False, no=False)
            opt.save()
        v = Voting(name='test voting', question=q)
        v.save()

        a, _ = Auth.objects.get_or_create(url=settings.BASEURL,
                                          defaults={'me': True, 'name': 'test auth'})
        a.save()
        v.auths.add(a)

        return v

    def create_binary_voting(self):
        q = Question(desc='binary question')
        q.save()
        opt = QuestionOption(question=q, option='', yes = True, no = False)
        opt.save()
        opt2 = QuestionOption(question=q, option='', yes = False, no = True)
        opt2.save()
        v = Voting(name='test voting', question=q)
        v.save()

        a, _ = Auth.objects.get_or_create(url=settings.BASEURL,
                                          defaults={'me': True, 'name': 'test auth'})
        a.save()
        v.auths.add(a)

        return v

    def create_voters(self, v):
        for i in range(100):
            u, _ = User.objects.get_or_create(username='testvoter{}'.format(i))
            u.is_active = True
            u.save()
            c = Census(voter_id=u.id, voting_id=v.id)
            c.save()

    def get_or_create_user(self, pk):
        user, _ = User.objects.get_or_create(pk=pk)
        user.username = 'user{}'.format(pk)
        user.set_password('qwerty')
        user.save()
        return user

    def store_votes(self, v):
        voters = list(Census.objects.filter(voting_id=v.id))
        voter = voters.pop()

        clear = {}
        for opt in v.question.options.all():
            clear[opt.number] = 0
            for i in range(random.randint(0, 5)):
                a, b = self.encrypt_msg(opt.number, v)
                data = {
                    'voting': v.id,
                    'voter': voter.voter_id,
                    'vote': { 'a': a, 'b': b },
                }
                clear[opt.number] += 1
                user = self.get_or_create_user(voter.voter_id)
                self.login(user=user.username)
                voter = voters.pop()
                mods.post('store', json=data)
        return clear


    def test_complete_voting(self):
        v = self.create_voting()
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        for q in v.question.options.all():
            self.assertEqual(tally.get(q.number, 0), clear.get(q.number, 0))

        for q in v.postproc:
            self.assertEqual(tally.get(q["number"], 0), q["votes"])

    def test_complete_binary_voting(self):
        v = self.create_binary_voting()
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        for q in v.question.options.all():
            self.assertEqual(tally.get(q.number, 0), clear.get(q.number, 0))

        for q in v.postproc:
            self.assertEqual(tally.get(q["number"], 0), q["votes"])

    def test_create_voting_from_api(self):
        data = {'name': 'Example'}
        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 400)

        data = {
            'name': 'Example',
            'desc': 'Description example',
            'question': 'I want a ',
            'question_opt': ['cat', 'dog', 'horse']
        }

        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 201)


    def test_update_voting(self):
        voting = self.create_voting()

        data = {'action': 'start'}
        #response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        #self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        data = {'action': 'bad'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)

        # STATUS VOTING: not started
        for action in ['stop', 'tally']:
            data = {'action': action}
            response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), 'Voting is not started')

        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting started')

        # STATUS VOTING: started
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting is not stopped')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting stopped')

        # STATUS VOTING: stopped
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting tallied')

        # STATUS VOTING: tallied
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already tallied')

    def test_update_binary_voting(self):
        voting = self.create_binary_voting()
        #Nota: en esencia es el mismo test que update_voting, pero es necesario para probar las
        # diferentes posibles interacciones del sistema con las nuevas opciones en las pregutas.

        data = {'action': 'start'}
        #response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        #self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        data = {'action': 'bad'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)

        # STATUS VOTING: not started
        for action in ['stop', 'tally']:
            data = {'action': action}
            response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), 'Voting is not started')

        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting started')

        # STATUS VOTING: started
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting is not stopped')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting stopped')

        # STATUS VOTING: stopped
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting tallied')

        # STATUS VOTING: tallied
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already tallied') 


# TESTS DE MODELOS

class votacionFalse(TestCase):
    def setUp(self):
            super().setUp()
            self.usuario= Auth(name='Manuel',url='http://localhost:8000/',me=True)
            self.usuario.save()
            self.pregunta= Question(desc='¿Crees que funcionara?')
            self.pregunta.save()
            self.voting = Voting(name='Votacion de Modelo', desc='Test 1 de modelo', public=False,question=self.pregunta)
            self.voting.save()
            self.voting.auths.add(self.usuario)
            self.voting.save()

    def tearDown(self):
            super().tearDown()
            self.voting = None

    def test_store_voting(self):
            self.assertEqual(Voting.objects.count(), 1)

class votacionTrue(TestCase):
    def setUp(self):
            super().setUp()
            self.usuario= Auth(name='Manuel',url='http://localhost:8000/',me=True)
            self.usuario.save()
            self.pregunta= Question(desc='¿Crees que funcionara?')
            self.pregunta.save()
            self.voting = Voting(name='Votacion de Modelo', desc='Test 1 de modelo', public=True,question=self.pregunta)
            self.voting.save()
            self.voting.auths.add(self.usuario)
            self.voting.save()

    def tearDown(self):
            super().tearDown()
            self.voting = None

    def test_store_voting(self):
            self.assertEqual(Voting.objects.count(), 1)

# TEST DE VISTAS

""" class TestSignUpCorrect(unittest.TestCase):

    def setUp(self):
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        self.driver = webdriver.Firefox(firefox_options=firefox_options)
        
    def test_signUpCorrect(self):
        self.driver.get("http://localhost:8000/admin/login/?next=/admin/")
        username = self.driver.find_element_by_id('id_username')
        username.clear
        username.send_keys("Minuke")
        password = self.driver.find_element_by_id('id_password')
        password.clear
        password.send_keys("decidegc")
        self.driver.find_element_by_xpath("//input[@value='Iniciar sesión']").click()
        self.assertTrue(len(self.driver.find_elements_by_id('user-tools'))>0)

    def tearDown(self):
        self.driver.quit

if __name__ == '__main__':
    unittest.main()

class TestSignUpIncorrect(unittest.TestCase):

    def setUp(self):
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        self.driver = webdriver.Firefox(firefox_options=firefox_options)
        
    def test_signUpInorrect(self):
        self.driver.get("http://localhost:8000/admin/login/?next=/admin/")
        username = self.driver.find_element_by_id('id_username')
        username.clear
        username.send_keys("xxxxxxxx")
        password = self.driver.find_element_by_id('id_password')
        password.clear
        password.send_keys("xxxxxxxx")
        self.driver.find_element_by_xpath("//input[@value='Iniciar sesión']").click()
        self.assertTrue(len(self.driver.find_elements_by_id('user-tools'))==0)

    def tearDown(self):
        self.driver.quit

if __name__ == '__main__':
    unittest.main()

class TestVotacionSiNo(unittest.TestCase):

    def setUp(self):
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        self.driver = webdriver.Firefox(firefox_options=firefox_options)

    def test_signUpCorrect(self):
        self.driver.get("http://localhost:8000/admin/login/?next=/admin/")
        username = self.driver.find_element_by_id('id_username')
        username.clear
        username.send_keys("Minuke")
        password = self.driver.find_element_by_id('id_password')
        password.clear
        password.send_keys("decidegc")
        self.driver.find_element_by_xpath("//input[@value='Iniciar sesión']").click()
        self.driver.find_element_by_xpath("//a[contains(@href, '/admin/voting/question/add/')]").click()
        pregunta = self.driver.find_element_by_id('id_desc')
        pregunta.clear
        pregunta.send_keys("¿Estas satisfecho con tu nota del M3?")
        opcion0 =  self.driver.find_element_by_id('id_options-0-number')
        opcion0.clear
        opcion0.send_keys(1)
        opcion1 =  self.driver.find_element_by_id('id_options-1-number')
        opcion1.clear
        opcion1.send_keys(2)
        self.driver.find_element_by_xpath('//input[@id="id_options-0-yes"]').click()
        self.driver.find_element_by_xpath('//input[@id="id_options-1-no"]').click()
        self.driver.find_element_by_xpath('//input[@name="_save"]').click()
        self.assertTrue(len(self.driver.find_elements_by_class_name('success'))>0)

    def tearDown(self):
        self.driver.quit

if __name__ == '__main__':
    unittest.main() """