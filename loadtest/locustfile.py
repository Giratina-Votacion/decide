import json

from random import choice

from locust import (
    HttpLocust,
    TaskSequence,
    TaskSet,
    seq_task,
    task,
)


HOST = "http://localhost:8000"
VOTING = 1

class DefHomeList(TaskSet):

    @task
    def index(self):
        self.client.get("/".format(VOTING))

class DefVisualizer(TaskSet):

    @task
    def index(self):
        self.client.get("/visualizer/{0}/".format(VOTING))

class DefVotingList(TaskSet):

    @task
    def index(self):
        self.client.get("/list")


class DefVotingUsersList(TaskSet):

    @task
    def index(self):
        self.client.get("/user/{0}".format(VOTING))


class DefVoters(TaskSequence):

    def on_start(self):
        with open('voters.json') as f:
            self.voters = json.loads(f.read())
        self.voter = choice(list(self.voters.items()))

    def on_quit(self):
        self.voter = None

    @seq_task(1)
    def login(self):
        username, pwd = self.voter
        self.token = self.client.post("/authentication/login/", {
            "username": username,
            "password": pwd,
        }).json()

    @seq_task(2)
    def getuser(self):
        self.user = self.client.post("/authentication/getuser/", self.token).json()

    @seq_task(3)
    def voting(self):
        headers = {
            'Authorization': 'Token ' + self.token.get('token'),
            'content-type': 'application/json'
        }
        self.client.post("/store/", json.dumps({
            "token": self.token.get('token'),
            "vote": {
                "a": "12",
                "b": "64"
            },
            "voter": self.user.get('id'),
            "voting": VOTING
        }), headers=headers)


class Visualizer(HttpLocust):
    host = HOST
    task_set = DefVisualizer
    last_wait_time = 0

    def wait_time(self):
        self.last_wait_time += 1
        return self.last_wait_time

class HomeList(HttpLocust):
    host = HOST
    task_set = DefHomeList

    last_wait_time = 0

    def wait_time(self):
        self.last_wait_time += 1
        return self.last_wait_time

class VotingList(HttpLocust):
    host = HOST
    task_set = DefVotingList

    last_wait_time = 0

    def wait_time(self):
        self.last_wait_time += 1
        return self.last_wait_time

class VotingUsersList(HttpLocust):
    host = HOST
    task_set = DefVotingUsersList

    last_wait_time = 0

    def wait_time(self):
        self.last_wait_time += 1
        return self.last_wait_time

class Voters(HttpLocust):
    host = HOST
    task_set = DefVoters
