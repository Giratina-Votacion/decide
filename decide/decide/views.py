from django.shortcuts import render
from voting.models import Voting, Question
from census.models import Census
from base.models import Auth
from django.http.response import HttpResponse
from django.contrib.auth.models import User

def home(request):
    return render(request, 'voting/home.html')


def listaVotaciones(request):
    votaciones=Voting.objects.all().filter(public = True)
    cuestiones=Question.objects.all()
    censo=Census.objects.all()
    autoridades=Auth.objects.all()
    return render(request, 'voting/vistaVotaciones.html', {'votaciones':votaciones, 'cuestiones':cuestiones, 'censo':censo, 'autoridades':autoridades})

def listaUsuarios(request, id):
    votaciones=Voting.objects.all()
    cuestiones=Question.objects.all()
    censo=Census.objects.all()
    autoridades=Auth.objects.all()
    usuarios=User.objects.all()
    documento= id
    return render(request,'voting/vistaUsuarios.html',{'votaciones':votaciones, 'usuarios':usuarios,'cuestiones':cuestiones, 'censo':censo, 'autoridades':autoridades,'documento':documento})
    