mkdir static/js
cd static/js
wget https://github.com/aFarkas/webshim/archive/1.15.8.zip
unzip 1.15.8.zip
rm 1.15.8.zip
mv webshim-1.15.8/js-webshim webshim
rm -r webshim-1.15.8
cd -
