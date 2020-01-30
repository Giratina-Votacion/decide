from django.shortcuts import render
from voting.models import Voting, Question

def home(request):
    return render(request, 'voting/home.html')


def listaVotaciones(request):
    votaciones=Voting.objects.all().filter(public = True)
    cuestiones=Question.objects.all()
    return render(request, 'voting/vistaVotaciones.html', {'votaciones':votaciones, 'cuestiones':cuestiones})