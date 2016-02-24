mkdir static/js
cd static/js
wget https://github.com/aFarkas/webshim/archive/1.15.8.zip --no-check-certificate
unzip 1.15.8
rm 1.15.8
mv webshim-1.15.8/js-webshim webshim
rm -r webshim-1.15.8
cd -
