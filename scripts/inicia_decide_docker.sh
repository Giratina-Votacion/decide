#!/bin/bash

echo "Este script borrará todas las imágenes y contenedores de docker existentes en el sistema, ¿está seguro de que quiere continuar? (S/n)"
	read c
	if [ "$c" != "s" ] && [ "$c" != "S" ]; then
		echo "Deteniendo script..."
		exit 1;
	else
		echo "Borrando directorio decide_auto..."
		sudo docker stop $(docker ps -a -q)
		sudo docker container prune -f
		sudo docker image prune -a -f
	fi

if [ -d ~/decide_auto/ ]; then
	echo "Ya existe una carpeta decide_auto. Seguir adelante borrará la actual. ¿Desea continuar? (S/n)"
	read c
	if [ "$c" != "s" ] && [ "$c" != "S" ]; then
		echo "Deteniendo script..."
		exit 1;
	else
		echo "Borrando directorio decide_auto..."
		rm -rf ~/decide_auto
	fi
fi

echo "¿Qué rama desea usar para el despliegue?"
read branch

mkdir ~/decide_auto
cd ~/decide_auto
apt-get install git
git clone https://github.com/giratina-votacion/decide.git

echo "Creando el archivo local_settings.py..."
cp ~/decide_auto/decide/scripts/settings_aux.py ~/decide_auto/decide/decide/local_settings.py

echo "Cambiando a la rama seleccionada..."
cd ~/decide_auto/decide
git checkout $branch

cd ~/decide_auto/decide/docker

sudo docker-compose up -d

echo "¿Quiere crear un usuario administrador del sistema? (S/n)"
read aux
if [ "$aux" != "s" ] && [ "$aux" != "S" ]; then
	echo "No se ha creado el usuario administrador"
else
	echo "Creando usuario administrador..."
	docker exec -ti decide_web./manage.py createsuperuser
fi

echo "¡Servicio Decide desplegado en docker!"
echo "Acceda a el en la dirección 10.5.0.1:8000"
