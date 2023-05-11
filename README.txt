A következő leírás az alkalmazás lokális elindítását írja le.
1. Python telepítése
2. Telepítésnél “Add Python to PATH” kipipálása
3. Virtuális környezet aktiválása a következő paranccsal a parancssorba:
	- Windows alatt:
		“flaskenv\bin\activate”
	- MacOS és Linux alatt:
		“source flaskenv/bin/activate”
4. pip3 feltelepítése a “python3 get-pip.py” sorral
5. Könyvtárak feltelepítése a “pip3 install -r requirements.txt” sorral
6. Adatbázis útvonalának átálítása az app.py fájlban az
“app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdatabase.db’ “ sorra
5. Alkalmazás indítása a “flask run” paranccsal


