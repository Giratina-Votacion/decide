#!/bin/bash



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

if [ -d ~/myvirtual/ ]; then
	echo "Ya existe un entorno virtual. Seguir adelante borrará el actual. ¿Desea continuar? (S/n)"
	read c2
	if [ "$c2" != "s" ] && [ "$c2" != "S" ]; then
		echo "Deteniendo script..."
		exit 1;
	else
		rm -rf ~/myvirtual
	fi
fi




mkdir ~/myvirtual

cd ~/myvirtual

echo "¿Qué rama desea usar para el despliegue?"
read branch
echo "Creando el entorno virtual para Decide"
apt install python3 python3-pip postgresql
python3 -m venv myvirtual
source myvirtual/bin/activate

echo "Entorno virtual creado"

mkdir ~/decide_auto
cd ~/decide_auto
apt-get install git
git clone https://github.com/giratina-votacion/decide.git

echo "Cambiando a la rama seleccionada..."
cd ~/decide_auto/decide
git checkout $branch

echo "Creando el archivo local_settings.py..."
cp ~/decide_auto/decide/scripts/settings_aux.py ~/decide_auto/decide/decide/local_settings.py
echo "Instalando requisitos..."
pip3 install -r ~/decide_auto/decide/requirements.txt

echo "Creando base de datos..."
sudo -u postgres -h localhost psql -c "create user decide with password 'decide'"
sudo -u postgres -h localhost psql -c "ALTER USER decide CREATEDB"
sudo -u postgres -h localhost psql -c "DROP DATABASE IF EXISTS decide"
sudo -u postgres -h localhost psql -c "create database decide owner 'decide'"

echo "Ejecutando migraciones..."
python3 ~/decide_auto/decide/decide/manage.py makemigrations
python3 ~/decide_auto/decide/decide/manage.py migrate


echo "¿Quiere crear un usuario administrador del sistema? (S/n)"
read aux
if [ "$aux" != "s" ] && [ "$aux" != "S" ]; then
	echo "No se ha creado el usuario administrador"
else
	echo "Creando usuario administrador..."
	python3 ~/decide_auto/decide/decide/manage.py createsuperuser
fi


echo "Desplegando el servidor"
python3 ~/decide_auto/decide/decide/manage.py runserver

