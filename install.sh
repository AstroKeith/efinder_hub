#!/bin/sh

echo "eFinder Hub install"
echo " "
echo "*****************************************************************************"
echo "Updating Pi OS & packages"
echo "*****************************************************************************"
sudo apt update
sudo apt upgrade -y
echo " "
echo "*****************************************************************************"
echo "Installing additional Debian and Python packages"
echo "*****************************************************************************"

sudo apt install -y python3-smbus

HOME=/home/efinder
cd $HOME
echo " "
echo "*****************************************************************************"
echo "Installing new astrometry packages"
echo "*****************************************************************************"
sudo apt install -y python3-skyfield

python -m venv /home/efinder/venv-efinder --system-site-packages

cd $HOME
echo " "
echo "*****************************************************************************"
echo "Downloading eFinder_Lite from AstroKeith GitHub"
echo "*****************************************************************************"
sudo -u efinder git clone https://github.com/AstroKeith/eFinder_hub.git
echo " "


echo "*****************************************************************************"
echo "Installing required packages"
echo "*****************************************************************************"
mkdir /home/efinder/Solver
mkdir /home/efinder/Solver/images
mkdir /home/efinder/Solver/data


cp /home/efinder/eFinder_hub/Solver/*.* /home/efinder/Solver


echo " "
echo "*****************************************************************************"
echo "Installing OLED & GPIO drivers"
echo "*****************************************************************************"
cd $HOME
wget https://github.com/joan2937/lg/archive/master.zip
unzip master.zip
cd lg-master
sudo make install
sudo apt install -y python3-rpi-lgpio
cd /home/efinder/Solver
unzip drive.zip

cd $HOME
echo " "
echo "*****************************************************************************"
echo "Installing Samba file share support"

sudo apt install -y samba samba-common-bin
sudo tee -a /etc/samba/smb.conf > /dev/null <<EOT
[efindershare]
path = /home/efinder
writeable=Yes
create mask=0777
directory mask=0777
public=no
EOT
username="efinder"
pass="efinder"
(echo $pass; sleep 1; echo $pass) | sudo smbpasswd -a -s $username
sudo systemctl restart smbd

cd $HOME

echo " "
echo "*****************************************************************************"
echo "Setting up web page server"
echo "*****************************************************************************"
sudo apt-get install -y apache2
sudo apt-get install -y php8.2
sudo chmod a+rwx /home/efinder
sudo chmod a+rwx /home/efinder/Solver
sudo chmod a+rwx /home/efinder/Solver/eFinder.config
sudo cp eFinder_hub/Solver/www/*.* /var/www/html
sudo mv /var/www/html/index.html /var/www/html/apacheindex.html
sudo chmod -R 755 /var/www/html

echo " "
echo "*****************************************************************************"
echo "Final eFinder_Lite configuration setting"
echo "*****************************************************************************"


sudo chmod a+rwx eFinder_hub/Solver/my_cron
sudo cp /home/efinder/eFinder_hub/Solver/my_cron /etc/cron.d

sudo raspi-config nonint do_ssh 0
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_serial_cons 1
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

sudo reboot now

