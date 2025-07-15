#!/bin/bash
## Script for building/installing FreeSWITCH from source.
## URL: https://gist.github.com/mariogasparoni/dc4490fcc85a527ac45f3d42e35a962c
## Freely distributed under the MIT license
##
##
set -xe
FREESWITCH_SOURCE=https://github.com/signalwire/freeswitch.git
FREESWITCH_RELEASE=master #or set this to any other version, for example: v1.10.5
PREFIX=/usr/share/freeswitch

# If you want to remove some modules from build, specify/uncomment it here
REMOVED_MODULES=(
   mod_signalwire
   mog_pgsql
)

#Clean old prefix and build
sudo rm -rf $PREFIX
rm -rf ~/build-$FREESWITCH_RELEASE

#install dependencies
#sudo apt-get update && sudo apt-get install -y git-core build-essential python python2-dev python3-dev autoconf automake cmake libtool libncurses5 libncurses5-dev make libjpeg-dev pkg-config zlib1g-dev sqlite3 libsqlite3-dev libpcre3-dev libspeexdsp-dev libedit-dev libldns-dev liblua5.1-0-dev libcurl4-gnutls-dev libapr1-dev yasm libsndfile-dev libopus-dev libtiff-dev libavformat-dev libswscale-dev libavresample-dev libpq-dev



#clone source and prepares it
mkdir -p ~/build-$FREESWITCH_RELEASE
cd ~/build-$FREESWITCH_RELEASE

PVERSION=( ${FREESWITCH_RELEASE//./ } )
MIN_VERSION=${PVERSION[1]}
PATCH_VERSION=${PVERSION[2]}

if [[ $FREESWITCH_RELEASE = "master" ]] || [[ $MIN_VERSION -ge 10  &&  $PATCH_VERSION -ge 3 ]]
then
    echo "VERSION => 1.10.3 - need to build libsk2, signalwire-c , spandsp and sofia-sip separatedly"

    #build and install libks2 - needed for mod_verto and signalwire
    git clone https://github.com/signalwire/libks.git
    cd libks
    cmake . -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=$PREFIX
    make
    sudo make install
    cd ..

    #build and install signalwire-c - needed for mod_signalwire
    git clone https://github.com/signalwire/signalwire-c
    cd signalwire-c
    env PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig cmake . -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=$PREFIX
    make
    sudo make install
    cd ..

    #build and install libspandev
    git clone https://github.com/freeswitch/spandsp.git
    cd spandsp
    git checkout 67d2455efe02e7ff0d897f3fd5636fed4d54549e # workaround for @signalwire/freeswitch#2158 (thx to @9to1url)
    ./bootstrap.sh
    ./configure --prefix=$PREFIX
    make
    sudo make install
    cd ..

    #build and install mod_sofia
    git clone https://github.com/freeswitch/sofia-sip.git
    cd sofia-sip
    ./bootstrap.sh
    ./configure --prefix=$PREFIX
    make
    sudo make install
    cd ..
fi

#avoid git access's denied error
touch .config && sudo chown $USER:$USER .config
if [ ! -d freeswitch ]
then
    git clone $FREESWITCH_SOURCE freeswitch
    cd freeswitch
else
    cd freeswitch
    git fetch origin
fi
git reset --hard $FREESWITCH_RELEASE && git clean -d -x -f

#remove modules from building
for module in "${REMOVED_MODULES[@]}"
do
    sed -i "s/applications\/mod_signalwire/#applications\/mod_signalwire/g" build/modules.conf.in
done
#sed -i "s/databases\/mod_pgsql/#databases\/mod_pgsql/g" build/modules.conf.in
sed -i "s/#applications\/mod_audio_stream/applications\/mod_audio_stream/g" build/modules.conf.in
./bootstrap.sh

#configure , build and install
env PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:/usr/local/lib/pkgconfig ./configure --prefix=$PREFIX --disable-libvpx

env C_INCLUDE_PATH=$PREFIX/include make
sudo make install config-vanilla

#package
cd ~/build-$FREESWITCH_RELEASE
tar zcvf freeswitch-$FREESWITCH_RELEASE.tar.gz $PREFIX
