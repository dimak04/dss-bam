#!/usr/bin/python
# coding=UTF-8

# Подключение внешних модулей
import ldap, os, string, random, time, sys, datetime, argparse

# Конфигурация Zimbra ldap
zdomain = "@domain.ru"
zldapSrv = "ip_addres"
zldapPort = "389"
zldapBinduser = "uid=admin,OU=people,DC=domain,DC=ru"
zldapPassword = "password"
zldapDefaultScope = "OU=people,DC=domain,DC=ru"
zldapSearchGroup = "CN=mail,OU=Group,OU=Office,DC=domain,DC=local"
zldapFields = ['sAMAccountName','sn','initials','title','givenName','displayName','company','telephoneNumber','mobile']
zldapFilter = "(&(objectclass=zimbraAccount)(uid=*))"
zreExcludeUsers = "^spam.*|^ham.*|^galsync.*|^admin$|^virus-quarantine.*|^addresskook*.*|^root*.*|^postmaster*.* "
zemailExpireDay = 365
zpathtozmprov="/opt/zimbra/bin/zmprov"
zper = zldapFields[1:]
zdefaultPassword = "Password"
now_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
veiwemenu ={"0":'''
Выбирите необходимое действие.
1 - backup - реревное копирование.
2 - restore from backup - восстановление резервной копии.
3 - migration - создание пакета файлов для переноса профилей пользователей на новый или резервный сервер.
4 - migration completion - завершение миграции.
9 - exit - выход и программы.''',"1":
'''
Backup - Резервное копирование!
Выбирите необходимое действие.
1 - all - резевное копирование всех профилей пользователей.
2 - user - резервное копирование указаного профиля пользователя.
0 - home - выход в главное меню.''',"2":
'''
Restor - Восстоновление!
1 - list - восстановление из списка.
2 - user - восстановление указаного профиля.
0 - home - выход в главное меню.''',"3":
'''
Migration - Перенос профилей пользователей!
Выбирите необходимое действия.
1 - all - перенос всех профилей пользователей.
2 - user - перенос указаного профиля.
0 - home - выход в главное меню.'''}
dialog = {"9":'Exit - выход.', "FIL": "Указаное значение не корректно. Повторите ввод."}

# Подключение к LDAP
def connectToLDAP(ldapSrv,ldapPort,ldapBinduser,ldapPassword):
    connect = ldap.initialize("LDAP://"+ldapSrv+":"+ldapPort)
    connect.simple_bind_s(ldapBinduser,ldapPassword)
   # print ("Соединение  - "+str(connect))
    return connect

# Получаем масив с донными о пользователях
def getUsersLDAP(connect,ldapDefaultScope,ldapFields,ldapFilter):
    users = connect.search_s(ldapDefaultScope,ldap.SCOPE_SUBTREE,ldapFilter,)
    return users

# Процедура резервного копирования		
def backup(par1, par2 = "ALL", backupfolder = "/backup/"):
	global zldapFilter
	userlist = []
	keyinput = ""
	if par1 == True:
		print ("Backup - Резервное копирование!")
		keyinput = raw_input("Укажите каталог для сохранения резервной копии (по умолчанию значение /backup/): ")
		if par2 != "ALL":
			par2 = raw_input("Введите имя профиля для резервного копирования")
			zldapFilter = "(&(objectclass=zimbraAccount)(uid="+par2+"))"
	else:
		if par2 != "ALL":
			zldapFilter = "(&(objectclass=zimbraAccount)(uid="+par2+"))"
			
	if keyinput != "":
		backupfolder = keyinput+par2+"_"+now_time
	else:
		backupfolder = backupfolder+par2+"_"+now_time
	os.system('mkdir '+backupfolder)
	os.system('chmod -R 777 '+backupfolder)
	# Открываем файл и записываем всех пользователей с параметрами создания на другом сервере
	fuserlist = open(backupfolder+"/userlist.txt", 'w')
	zconnetLDAP = connectToLDAP(zldapSrv,zldapPort,zldapBinduser,zldapPassword)
	zusersLDAP = getUsersLDAP(zconnetLDAP,zldapDefaultScope,zldapFields,zldapFilter)
	# Запись атрибутов пользователе в файл
	for searchUsers in zusersLDAP:
		per = searchUsers[1]
		uidTU = per["uid"][0]
		userlist.append(uidTU)
		addstring = "ca "+uidTU+zdomain+" "+zdefaultPassword
		for srper in zper:
			if srper in per:
				addstring += " "+srper+" '"+per[srper][0]+"'"
				addstring += "\n"
		fuserlist.write(addstring)
	# --------------------------------------	
	# Запускаем процедуру выгрузки профиля пользователей из списка 
	for profileUser in userlist:
		goBack = 'su - zimbra -c \"zmmailbox -z -m '+profileUser+zdomain+' -t 0 getRestURL "//?fmt=tgz" > '+backupfolder+'/'+profileUser+'.tgz\"'
		print ("Копирование профиля - "+profileUser)
		os.system(goBack)

		
# Востановление резервной копии
def restore(par1, par2 = "ALL", backupfolder = "/backup/"):
	userlist = {}
	keyinput = ""
	if par1 == True:
		print ("Sertore - Востановление резервной копии!")
		keyinput = raw_input("Укажите каталог восстонавливаемой резервной копии (по умолчанию значение /backup/): ")
		if keyinput != "":
			backupfolder = keyinput
		if os.path.exists(backupfolder):
			if par2 != "ALL":
				par2 = raw_input("Введите имя профиля для восстановления: ")
				restor_file = backupfolder+par2+".tgz"
				if os.path.exists(restor_file):
					userlist[par2] = "md"
					for profileUser in userlist.keys():
						goBack = 'su - zimbra -c \"zmmailbox -z -m '+profileUser+zdomain+' -t 0 postRestURL "//?fmt=tgz&resolve=reset" > '+restor_file+'\"'
						print ("Восстоновление профиля - "+profileUser)
						#os.system(goBack)
				else:
					print("Файл не найден! Проверте наличие файла для восстановления.")
					continue
			else:
				all_files = os.listdir(backupfolder)
				for chek_file in all_files:
					arg_file = os.path.splitext(chek_file)
					if arg_file[1] == ".tgz":
						userlist[arg_file[0]] = "md"
					
				for r_user in  userlist.keys():
					restor_file = backupfolder+r_user+".tgz"
					goBack = 'su - zimbra -c \"zmmailbox -z -m '+r_user+zdomain+' -t 0 postRestURL "//?fmt=tgz&resolve=reset" > '+restor_file+'\"'
						print ("Восстоновление профиля - "+r_user)
						#os.system(goBack)
		else:
			print("Указанный каталог не существует.")
	else:
		if os.path.exists(backupfolder):
			if par2 != "ALL":
				par2 = raw_input("Введите имя профиля для восстановления: ")
				restor_file = backupfolder+par2+".tgz"
				if os.path.exists(restor_file):
					userlist[par2] = "md"
					for profileUser in userlist.keys():
						goBack = 'su - zimbra -c \"zmmailbox -z -m '+profileUser+zdomain+' -t 0 postRestURL "//?fmt=tgz&resolve=reset" > '+restor_file+'\"'
						print ("Восстоновление профиля - "+profileUser)
						#os.system(goBack)
				else:
					print("Файл не найден! Проверте наличие файла для восстановления.")
					continue
			else:
				all_files = os.listdir(backupfolder)
				for chek_file in all_files:
					arg_file = os.path.splitext(chek_file)
					if arg_file[1] == ".tgz":
						userlist[arg_file[0]] = "md"
					
				for r_user in  userlist.keys():
					restor_file = backupfolder+r_user+".tgz"
					goBack = 'su - zimbra -c \"zmmailbox -z -m '+r_user+zdomain+' -t 0 postRestURL "//?fmt=tgz&resolve=reset" > '+restor_file+'\"'
						print ("Восстоновление профиля - "+r_user)
						#os.system(goBack)
		else:
			print("Указанный каталог не существует.")
			
# Очистка консоли			
def clearConsol():
	if sys.platform == 'win32':os.system('cls')
	else:os.system('clear')

def controlInput(ai):
	if raw_input().type != 'Ineger':
		return None
	else:
		return raw_input()

def cheakArg():
        parser = argparse.ArgumentParser(description="Программа резервного копирования и восстановления.")
        parser.add_argument("-act1", type=str, default = "", help="Параметр основного действия")
        parser.add_argument("-act2", type=str, default = "", help="Параметр втоичного действия")
        parser.add_argument("-dirB", type=str, default = "", help="Дириктория резервного копирования")
        arg = parser.parse_args()
        return arg		
		
# MAIN

if not cheakArg().act1:
	console = True
	clearConsol()
	print ("'DSS-soft-zmb' Скрипт резервного копирования и востоновление, миграция пользователей на новый сервер Zimbra")
	keyhomemenu = "0"
	while keyhomemenu != "9":
		print(veiwemenu[keyhomemenu])
		# Резервное копирование
		if keyhomemenu == "1":
			while True:
				keymenu1 = raw_input()
				if keymenu1 == "1":
					backup(console)
					break
				elif keymenu1 == "2":
					backup(console,"USER")
					break
				elif keymenu1 == "0":
					break
				else:
					clearConsol()
					print(dialog["FIL"])
					print(veiwemenu[keyhomemenu])
			keyhomemenu = keymenu1
			clearConsol()
			continue
		# Восстоновление
		elif keyhomemenu == "2":
			while True:
				keymenu2 = raw_input()
				if keymenu2 == "1":
					restore(console)
					break
				elif keymenu2 == "2":
					restore(console,"USER")
					break
				elif keymenu2 == "0":
					break
				else:
					clearConsol()
					print(dialog["FIL"])
					print(veiwemenu[keyhomemenu])
			keyhomemenu = keymenu2
			clearConsol()
			continue	
		# Восстоновление из Бэкапа
		elif keyhomemenu == "3":
			keymenu3 = raw_input()
		else:
			keyhomemenu = raw_input()
		clearConsol()
	print (dialog[keyhomemenu])	
else:
	filter = veiwemenu.keys()
	filter.sort()
	console = False
	if cheakArg().act1 in filter[1:]:
		backup(console,cheakArg().act2,cheakArg().dirB)
	else:
		print(dialog["FIL"])
