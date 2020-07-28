#!/bin/bash
# script version v2.0-rc0
# From https://github.com/ferion11/LogosLinuxInstaller

# version of Logos from: https://wiki.logos.com/The_Logos_8_Beta_Program
export LOGOS_URL="https://downloads.logoscdn.com/LBS8/Installer/8.15.0.0004/Logos-x86.msi"
export LOGOS64_URL="https://downloads.logoscdn.com/LBS8/Installer/8.15.0.0004/Logos-x64.msi"
export WINE_APPIMAGE_URL="https://github.com/ferion11/Wine_Appimage/releases/download/continuous/wine-i386_x86_64-archlinux.AppImage"
export WINETRICKS_URL="https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
#LOGOS_MVERSION=$(echo $LOGOS_URL | cut -d/ -f4)
#export LOGOS_MVERSION
LOGOS_VERSION=$(echo $LOGOS_URL | cut -d/ -f6)
LOGOS_MSI=$(echo $LOGOS_URL | cut -d/ -f7)
LOGOS64_MSI=$(echo $LOGOS64_URL | cut -d/ -f7)
export LOGOS_VERSION
export LOGOS_MSI
export LOGOS64_MSI

export WORKDIR="/tmp/workingLogosTemp"
if [ -z "$INSTALLDIR" ]; then export INSTALLDIR="$HOME/LogosBible_Linux_P" ; fi

export APPDIR="${INSTALLDIR}/data"
export APPDIR_BIN="$APPDIR/bin"
export APPIMAGE_NAME="wine-i386_x86_64-archlinux.AppImage"

#DOWNLOADED_RESOURCES=""


#======= Aux =============
die() { echo >&2 "$*"; exit 1; };

have_dep() {
	command -v "$1" >/dev/null 2>&1
}

clean_all() {
	echo "Cleaning all temp files..."
	rm -rf "$WORKDIR"
	echo "done"
}

#zenity------
gtk_info() {
	zenity --info --width=300 --height=200 --text="$*" --title='Information'
}
gtk_warn() {
	zenity --warning --width=300 --height=200 --text="$*" --title='Warning!'
}
gtk_error() {
	zenity --error --width=300 --height=200 --text="$*" --title='Error!'
}
gtk_fatal_error() {
	gtk_error "$@"
	echo "End!"
	exit 1
}

mkdir_critical() {
	mkdir "$1" || gtk_fatal_error "Can't create the $1 directory"
}

gtk_question() {
	if zenity --question --width=300 --height=200 --text "$@" --title='Question:'
	then
		return 0
	else
		return 1
	fi
}
gtk_continue_question() {
	if ! gtk_question "$@"; then
		gtk_fatal_error "The installation is cancelled!"
	fi
}

gtk_download() {
	# $1	what to download
	# $2	where into
	# NOTE: here must be limitation to handle it easily. $2 can be dir, if it already exists or if it ends with '/'

	URI="$1"
	# extract last field of URI as filename:
	FILENAME="${URI##*/}"

	if [ "$2" != "${2%/}" ]; then
		# it has '/' at the end or it is existing directory
		TARGET="$2/${1##*/}"
		[ -d "$2" ] || mkdir -p "$2" || gtk_fatal_error "Cannot create $2"
	elif [ -d "$2" ]; then
		# it's existing directory
		TARGET="$2/${1##*/}"
	else
		# $2 is file
		TARGET="$2"
		# ensure that directory, where the target file will be exists
		[ -d "${2%/*}" ] || mkdir -p "${2%/*}" || gtk_fatal_error "Cannot create directory ${2%/*}"
	fi

	echo "* Downloading:"
	echo "$1"
	echo "into:"
	echo "$2"

	pipe="/tmp/.pipe__gtk_download__function"
	rm -rf $pipe
	mkfifo $pipe

	# download with output to dialog progress bar
	total_size="Starting..."
	percent="0"
	current="Starting..."
	speed="Starting..."
	remain="Starting..."
	wget -c "$1" -O "$TARGET" 2>&1 | while read -r data; do
		#if [ "$(echo "$data" | grep '^Length:')" ]; then
		if echo "$data" | grep -q '^Length:' ; then
			result=$(echo "$data" | grep "^Length:" | sed 's/.*\((.*)\).*/\1/' |  tr -d '()')
			if [ ${#result} -le 10 ]; then total_size=${result} ; fi
		fi

		#if [ "$(echo "$data" | grep '[0-9]*%' )" ];then
		if echo "$data" | grep -q '[0-9]*%' ;then
			result=$(echo "$data" | grep -o "[0-9]*%" | tr -d '%')
			if [ ${#result} -le 3 ]; then percent=${result} ; fi

			result=$(echo "$data" | grep "[0-9]*%" | sed 's/\([0-9BKMG]\+\).*/\1/' )
			if [ ${#result} -le 10 ]; then current=${result} ; fi

			result=$(echo "$data" | grep "[0-9]*%" | sed 's/.*\(% [0-9BKMG.]\+\).*/\1/' | tr -d ' %')
			if [ ${#result} -le 10 ]; then speed=${result} ; fi

			result=$(echo "$data" | grep -o "[0-9A-Za-z]*$" )
			if [ ${#result} -le 10 ]; then remain=${result} ; fi
		fi

		# report
		echo "$percent"
		# shellcheck disable=SC2028
		echo "#Downloading: $FILENAME\ninto: $2\n\n$current of $total_size ($percent%)\nSpeed : $speed/Sec\nEstimated time : $remain"
	done > $pipe &

	zenity --progress --title "Downloading $FILENAME..." --text="Downloading: $FILENAME\ninto: $2\n" --percentage=0 --auto-close --auto-kill < $pipe

	if [ "$?" = -1 ] ; then
		#pkill -15 wget
		killall -15 wget
		rm -rf $pipe
		gtk_fatal_error "The installation is cancelled!"
	fi

	rm -rf $pipe
}

#--------------
#==========================


#======= Basic Deps =============
echo 'Searching for dependencies:'

if [ "$(id -u)" = 0 ]; then
	echo "* Running Wine/winetricks as root is highly discouraged. See https://wiki.winehq.org/FAQ#Should_I_run_Wine_as_root.3F"
fi

if [ -z "$DISPLAY" ]; then
	echo "* You want to run without X, but it don't work."
	exit 1
fi

if have_dep zenity; then
	echo '* Zenity is installed!'
else
	echo '* Your system does not have Zenity. Please install Zenity package.'
	exit 1
fi

if have_dep wget; then
	echo '* wget is installed!'
else
	gtk_fatal_error "Your system does not have wget. Please install wget package."
fi

if have_dep find; then
	echo '* command find is installed!'
else
	gtk_fatal_error "Your system does not have command find. Please install command find package."
fi

if have_dep sed; then
	echo '* command sed is installed!'
else
	gtk_fatal_error "Your system does not have command sed. Please install command sed package."
fi

if have_dep grep; then
	echo '* command grep is installed!'
else
	gtk_fatal_error "Your system does not have command grep. Please install command grep package."
fi

echo "Starting Zenity GUI..."
#==========================


#======= Main =============

if [ -d "$INSTALLDIR" ]; then
	gtk_fatal_error "One directory already exists in ${INSTALLDIR}, please remove/rename it or use another location by setting the INSTALLDIR variable"
fi

installationChoice="$(zenity --width=400 --height=250 \
	--title="Question: Install Logos Bible" \
	--text="This script will create one directory in (can changed by setting the INSTALLDIR variable):\n\"${INSTALLDIR}\"\nto be one installation of LogosBible v$LOGOS_VERSION independent of others installations.\nPlease, select the type of installation:" \
	--list --radiolist --column "S" --column "Descrition" \
	TRUE "1- Install LogosBible32 using Wine AppImage (default)." \
	FALSE "2- Install LogosBible32 using the native Wine." \
	FALSE "3- Install LogosBible64 using the native Wine64 (unstable)." )"

case "${installationChoice}" in
	1*)
		echo "Installing LogosBible 32bits using Wine AppImage..."
		export WINEARCH=win32
		export WINEPREFIX="$APPDIR/wine32_bottle"
		;;
	2*)
		echo "Installing LogosBible 32bits using the native Wine..."
		export NO_APPIMAGE="1"
		export WINEARCH=win32
		export WINEPREFIX="$APPDIR/wine32_bottle"

		# check for wine installation
		WINE_VERSION_CHECK="$(wine --version)"
		if [ -z "${WINE_VERSION_CHECK}" ]; then
			gtk_fatal_error "Wine not found! Please install native Wine first."
		fi
		echo "Using: ${WINE_VERSION_CHECK}"
		;;
	3*)
		echo "Installing LogosBible 64bits using the native Wine..."
		export NO_APPIMAGE="1"
		export WINEARCH=win64
		export WINEPREFIX="$APPDIR/wine64_bottle"

		# check for wine installation
		WINE_VERSION_CHECK="$(wine64 --version)"
		if [ -z "${WINE_VERSION_CHECK}" ]; then
			gtk_fatal_error "Wine64 not found! Please install native Wine64 first."
		fi
		echo "Using: ${WINE_VERSION_CHECK}"
		;;
	*)
		gtk_fatal_error "Installation canceled!"
esac

# Making the setup:
mkdir -p "$WORKDIR"
mkdir -p "$INSTALLDIR"
mkdir_critical "$APPDIR"

if [ -z "$NO_APPIMAGE" ]; then
	echo "Using AppImage..."
	#-------------------------
	# Geting the AppImage:
	if [ -f "${DOWNLOADED_RESOURCES}/${APPIMAGE_NAME}" ]; then
		echo "${APPIMAGE_NAME} exist. Using it..."
		cp "${DOWNLOADED_RESOURCES}/${APPIMAGE_NAME}" "${APPDIR}/" | zenity --progress --title="Copying..." --text="Copying: $APPIMAGE_NAME\ninto: $APPDIR" --pulsate --auto-close
		cp "$WORKDIR/$APPIMAGE_NAME.zsync" "$APPDIR" | zenity --progress --title="Copying..." --text="Copying: $APPIMAGE_NAME.zsync\ninto: $APPDIR" --pulsate --auto-close
	else
		echo "${APPIMAGE_NAME} does not exist. Downloading..."
		gtk_download "${WINE_APPIMAGE_URL}" "$WORKDIR"

		mv "$WORKDIR/$APPIMAGE_NAME" "$APPDIR" | zenity --progress --title="Moving..." --text="Moving: $APPIMAGE_NAME\ninto: $APPDIR" --pulsate --auto-close

		gtk_download "${WINE_APPIMAGE_URL}.zsync" "$WORKDIR"
		mv "$WORKDIR/$APPIMAGE_NAME.zsync" "$APPDIR" | zenity --progress --title="Moving..." --text="Moving: $APPIMAGE_NAME.zsync\ninto: $APPDIR" --pulsate --auto-close
	fi
	FILE="$APPDIR/$APPIMAGE_NAME"
	chmod +x "${FILE}"

	# Making the links (and dir)
	mkdir_critical "${APPDIR_BIN}"
	ln -s "$FILE" "${APPDIR_BIN}/wine"
	ln -s "$FILE" "${APPDIR_BIN}/wineserver"

	export PATH="${APPDIR_BIN}":$PATH
	#-------------------------
fi

gtk_continue_question "Now the script will create and configure the Wine Bottle on ${WINEPREFIX}. You can cancel the instalation of Mono. Do you wish to continue?"
wine wineboot | zenity --progress --title="Wineboot" --text="Wine is updating ${WINEPREFIX}..." --pulsate --auto-close

cat > "${WORKDIR}"/disable-winemenubuilder.reg << EOF
REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\DllOverrides]
"winemenubuilder.exe"=""


EOF

cat > "${WORKDIR}"/renderer_gdi.reg << EOF
REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Direct3D]
"DirectDrawRenderer"="gdi"
"renderer"="gdi"


EOF

wine regedit.exe "${WORKDIR}"/disable-winemenubuilder.reg | zenity --progress --title="Wine regedit" --text="Wine is blocking in $WINEPREFIX:\nfiletype associations, add menu items, or create desktop links" --pulsate --auto-close
wine regedit.exe "${WORKDIR}"/renderer_gdi.reg | zenity --progress --title="Wine regedit" --text="Wine is changing the renderer to gdi:\nthe old DirectDrawRenderer and the new renderer key" --pulsate --auto-close

gtk_continue_question "Now the script will install the winetricks packages on ${WINEPREFIX}. Do you wish to continue?"

gtk_download "${WINETRICKS_URL}" "$WORKDIR"
chmod +x "$WORKDIR/winetricks"

$WORKDIR/winetricks -q corefonts | zenity --progress --title="Winetricks" --text="Winetricks installing corefonts" --pulsate --auto-close
#$WORKDIR/winetricks -q ddr=gdi | zenity --progress --title="Winetricks" --text="Winetricks setting ddr=gdi..." --pulsate --auto-close
$WORKDIR/winetricks -q settings fontsmooth=rgb | zenity --progress --title="Winetricks" --text="Winetricks setting fontsmooth=rgb..." --pulsate --auto-close

$WORKDIR/winetricks -q dotnet48 | zenity --progress --title="Winetricks" --text="Winetricks installing DotNet v4.0 and v4.8 update (It might take a while)..." --pulsate --auto-close

gtk_continue_question "Now the script will download and install Logos Bible on ${WINEPREFIX}. You will need to interact with the installer. Do you wish to continue?"


#======= making the starting scripts ==============
create_starting_scripts_32() {
	echo "Creating starting scripts for LogosBible 32bits..."
	#------- Logos.sh -------------
	cat > "${WORKDIR}"/Logos.sh << EOF
#!/bin/bash

#------------- Starting block --------------
HERE="\$(dirname "\$(readlink -f "\${0}")")"

# Save IFS
IFS_TMP=\$IFS
IFS=$'\n'

#-------------------------------------------
export PATH="\${HERE}/data/bin:\${PATH}"
export WINEARCH=win32
export WINEPREFIX="\${HERE}/data/wine32_bottle"
#-------------------------------------------

# wine Run:
if [ "\$1" = "wine" ] ; then
	echo "======= Running wine only: ======="
	shift
	wine "\$@"
	echo "======= wine run done! ======="
	exit 0
fi

# winetricks Run:
if [ "\$1" = "winetricks" ] ; then
	echo "======= Running winetricks only: ======="
	wget -c -P /tmp https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
	chmod +x /tmp/winetricks
	shift
	/tmp/winetricks "\$@"
	rm -rf /tmp/winetricks
	echo "======= winetricks run done! ======="
	exit 0
fi

LOGOS_EXE=\$(find \${WINEPREFIX} -name Logos.exe | grep "Logos\/Logos.exe")
if [ -z "\$LOGOS_EXE" ] ; then
	echo "======= Running control: ======="
	"\${HERE}/controlPanel.sh"
	echo "======= control run done! ======="
	exit 0
fi

wine "\${LOGOS_EXE}"

#------------- Ending block ----------------
# restore IFS
IFS=\$IFS_TMP
#-------------------------------------------
EOF
	#------------------------------
	chmod +x "${WORKDIR}"/Logos.sh
	mv "${WORKDIR}"/Logos.sh "${INSTALLDIR}"/

	#------- controlPanel.sh ------
	cat > "${WORKDIR}"/controlPanel.sh << EOF
#!/bin/bash

#------------- Starting block --------------
HERE="\$(dirname "\$(readlink -f "\${0}")")"

# Save IFS
IFS_TMP=\$IFS
IFS=$'\n'

#-------------------------------------------
export PATH="\${HERE}/data/bin:\${PATH}"
export WINEARCH=win32
export WINEPREFIX="\${HERE}/data/wine32_bottle"
#-------------------------------------------

# wine Run:
if [ "\$1" = "wine" ] ; then
	echo "======= Running wine only: ======="
	shift
	wine "\$@"
	echo "======= wine run done! ======="
	exit 0
fi

# winetricks Run:
if [ "\$1" = "winetricks" ] ; then
	echo "======= Running winetricks only: ======="
	wget -c -P /tmp https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
	chmod +x /tmp/winetricks
	shift
	/tmp/winetricks "\$@"
	rm -rf /tmp/winetricks
	echo "======= winetricks run done! ======="
	exit 0
fi

wine control

#------------- Ending block ----------------
# restore IFS
IFS=\$IFS_TMP
#-------------------------------------------
EOF
	#------------------------------
	chmod +x "${WORKDIR}"/controlPanel.sh
	mv "${WORKDIR}"/controlPanel.sh "${INSTALLDIR}"/
}

create_starting_scripts_64() {
	echo "Creating starting scripts for LogosBible 64bits..."
	#------- Logos.sh -------------
	cat > "${WORKDIR}"/Logos.sh << EOF
#!/bin/bash

#------------- Starting block --------------
HERE="\$(dirname "\$(readlink -f "\${0}")")"

# Save IFS
IFS_TMP=\$IFS
IFS=$'\n'

#-------------------------------------------
export PATH="\${HERE}/data/bin:\${PATH}"
export WINEARCH=win64
export WINEPREFIX="\${HERE}/data/wine64_bottle"
#-------------------------------------------

# wine Run:
if [ "\$1" = "wine" ] ; then
	echo "======= Running wine only: ======="
	shift
	wine "\$@"
	echo "======= wine run done! ======="
	exit 0
fi

# winetricks Run:
if [ "\$1" = "winetricks" ] ; then
	echo "======= Running winetricks only: ======="
	wget -c -P /tmp https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
	chmod +x /tmp/winetricks
	shift
	/tmp/winetricks "\$@"
	rm -rf /tmp/winetricks
	echo "======= winetricks run done! ======="
	exit 0
fi

LOGOS_EXE=\$(find \${WINEPREFIX} -name Logos.exe | grep "Logos\/Logos.exe")
if [ -z "\$LOGOS_EXE" ] ; then
	echo "======= Running control: ======="
	"\${HERE}/controlPanel.sh"
	echo "======= control run done! ======="
	exit 0
fi

wine "\${LOGOS_EXE}"

#------------- Ending block ----------------
# restore IFS
IFS=\$IFS_TMP
#-------------------------------------------
EOF
	#------------------------------
	chmod +x "${WORKDIR}"/Logos.sh
	mv "${WORKDIR}"/Logos.sh "${INSTALLDIR}"/

	#------- controlPanel.sh ------
	cat > "${WORKDIR}"/controlPanel.sh << EOF
#!/bin/bash

#------------- Starting block --------------
HERE="\$(dirname "\$(readlink -f "\${0}")")"

# Save IFS
IFS_TMP=\$IFS
IFS=$'\n'

#-------------------------------------------
export PATH="\${HERE}/data/bin:\${PATH}"
export WINEARCH=win64
export WINEPREFIX="\${HERE}/data/wine64_bottle"
#-------------------------------------------

# wine Run:
if [ "\$1" = "wine" ] ; then
	echo "======= Running wine only: ======="
	shift
	wine "\$@"
	echo "======= wine run done! ======="
	exit 0
fi

# winetricks Run:
if [ "\$1" = "winetricks" ] ; then
	echo "======= Running winetricks only: ======="
	wget -c -P /tmp https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
	chmod +x /tmp/winetricks
	shift
	/tmp/winetricks "\$@"
	rm -rf /tmp/winetricks
	echo "======= winetricks run done! ======="
	exit 0
fi

wine control

#------------- Ending block ----------------
# restore IFS
IFS=\$IFS_TMP
#-------------------------------------------
EOF
	#------------------------------
	chmod +x "${WORKDIR}"/controlPanel.sh
	mv "${WORKDIR}"/controlPanel.sh "${INSTALLDIR}"/
}
#==================================================


# Geting and install the LogosBible:
case "$WINEARCH" in
	win32)
		echo "Installing LogosBible 32bits..."
		if [ -f "${DOWNLOADED_RESOURCES}/${LOGOS_MSI}" ]; then
			echo "${LOGOS_MSI} exist. Using it..."
		else
			echo "${LOGOS_MSI} does not exist. Downloading..."
			gtk_download "${LOGOS_URL}" "$WORKDIR"
		fi
		wine msiexec /i "${WORKDIR}"/"${LOGOS_MSI}" | zenity --progress --title="Logos Bible Installer" --text="Starting the Logos Bible Installer...\nNOTE: Will need interaction" --pulsate --auto-close
		create_starting_scripts_32
		;;
	win64)
		echo "Installing LogosBible 64bits..."
		if [ -f "${DOWNLOADED_RESOURCES}/${LOGOS64_MSI}" ]; then
			echo "${LOGOS64_MSI} exist. Using it..."
		else
			echo "${LOGOS64_MSI} does not exist. Downloading..."
			gtk_download "${LOGOS64_URL}" "$WORKDIR"
		fi
		wine msiexec /i "${WORKDIR}"/"${LOGOS64_MSI}" | zenity --progress --title="Logos Bible Installer" --text="Starting the Logos Bible Installer...\nNOTE: Will need interaction" --pulsate --auto-close
		create_starting_scripts_64
		;;
	*)
		gtk_fatal_error "Installation failed!"
esac

if gtk_question "Do you want to clean the temp files?"; then
	clean_all
fi

if gtk_question "Logos Bible Installed!\nYou can run it using the script Logos.sh inside ${INSTALLDIR}.\nDo you want to run it now?\nNOTE: Just close the error on the first execution."; then
	"${INSTALLDIR}"/Logos.sh
fi

echo "End!"
exit 0
#==========================
