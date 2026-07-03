import os
import sys
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # Logika mendeteksi folder virtual terisolasi (.exe) milik PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        dir_path = sys._MEIPASS  # Kunci lokasi internal di dalam tubuh .exe
    else:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        
    # Paksa sistem beroperasi di dalam folder internal tersebut
    os.chdir(dir_path)
    app_path = os.path.join(dir_path, "app.py")

    # Jalankan Streamlit secara pop-up otomatis
    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--server.headless=false",
        "--server.fileWatcherType=none",
        "--global.developmentMode=false"
    ]
    sys.exit(stcli.main())