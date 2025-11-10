from google_sheets_master import GoogleSheetsMaster

master = GoogleSheetsMaster()
territories = master.read_territories('1bhmLdyBU9-rYmzBj-C6GwMXZCe9fvdb_hKd62S19Pvs')
print(territories)