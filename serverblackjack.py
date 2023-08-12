#!/usr/bin/env python3
# -*- coding: utf-8 -

from sys import argv
from socket import gethostbyname
import asyncio
import time
import random

tables = {} # On stocke les tables crees par les croupiers
players = ['server'] # La liste des joueurs ayant rejoint une partie
parties = {} # On stocke les nouvelles parties a leur creation
partiesInProgress = {} # On stocke la liste des parties en cours avec leurs participants
cartes = ['as','valet','dame','roi','2','3','4','5','6','7','8','9','10','as','valet','dame','roi','2','3','4','5','6','7','8','9','10',
            'as','valet','dame','roi','2','3','4','5','6','7','8','9','10','as','valet','dame','roi','2','3','4','5','6','7','8','9','10']
partiesInProgressCartes = {} # chaque partie doit avoir ses propres cartes
adr_writer= {}
endPartiesUsers={}

async def handle_request_joueur(reader, writer):

    # On recupere l'addresse IP de l'utilisateur et on l'ajoute dans la table users avant de l'envoyer un message de bienvenue
    addr = writer.get_extra_info('peername')[0]
    players.append(addr)
    adr_writer[addr]=(reader,writer)
    print(f'User {addr} is connected')

    message = f"Bienvenue User {addr}. Voici la liste des tables disponibles : "

    # On constitue le message de bienvenue en affichant au joueur les tables disponibles
    n = 0
    for item in tables.keys() :
        if n < len(tables)-1:
            message+=item+","
        else : message+=item+"."
        n+=1

    # On envoie le message de bienveue au joueur qui s'est connecte
    writer.write((message+"\r\n").encode())
    await writer.drain()

    # On recupere le nom de la table donne par le joueur
    data = await reader.readline()
    table = data[5:len(data)-2].decode()

    # Si la table n'est pas creee au prealable par un croupier on ferme la session du joueur
    if table not in tables.keys() :
        players.remove(addr)
        adr_writer.pop(addr)
        writer.write("END\r\n".encode())
    else :
        # Si aucun joueur n'a cree une partie avec la table, on en cree et on l'ajoute sur la liste des joueurs jouant a cette table
        # et on initie le temps de la creation de la partie
        if table not in parties.keys() :
            parties[table]=['server',addr] # Le serveur doit etre de chaque partie
            await asyncio.sleep(tables.get(table))
            tables.pop(table)
            await initialisation(table)
        else : # S'il y'a des joueurs en attente dans une partie sur cete table, on ajoute le joueur comme participant a cette table
            users = parties.get(table)
            users.append(addr)
            parties.update({table:users})

        # partyUsers = parties.get(table)
        print(f"Les participants de la table {table} sont {parties.get(table)}")




async def initialisation(party) :
    
    usersCartes = {}

    for user in parties.get(party) :

        usersCartes[user]=[]
    
    parties.pop(party)

    partiesInProgress[party]=usersCartes
    partiesInProgressCartes[party]=cartes.copy()

    usersCartes = partiesInProgress.get(party)
    partyCartes = partiesInProgressCartes.get(party) # On recupere les cartes de la partie

    # On parcours les joueurs de cette partie deux fois en les distribuants des cartes
    for i in range(2):
        for user in usersCartes.keys() :
            # Si l'utiilisateur est le serveur et qu'on est dans le deuxieme tour, on continue sans lui attribuer une carte
            if i==1 :
                if user == 'server':
                    continue
                else : # Si le joueur courant n'est pas le serveur, on distribue les cartes
                    userCartes = usersCartes.get(user) # On recupere la liste des cartes du joueur courant
                    carte = partyCartes[random.randrange(0, len(partyCartes))] # On prend une carte au hasard
                    userCartes.append(carte) # On ajoute la carte recupere au hazard a la liste des cartes du joueur courant
                    partyCartes.remove(carte) # On supprime la carte prise au hasard de la liste des cartes de la partie

            else:
                userCartes = usersCartes.get(user) # On recupere la liste des cartes du joueur courant
                carte = partyCartes[random.randrange(0, len(partyCartes))] # On prend une carte au hasard
                userCartes.append(carte) # On ajoute la carte recupere au hazard a la liste des cartes du joueur courant
                partyCartes.remove(carte) # On supprime la carte prise au hasard de la liste des cartes de la partie

    partiesInProgressCartes.update({party:partyCartes}) # O met a jour la liste des cartes de la partie

    # On affiche a tous les joueurs de la partie la premiere carte du serveur
    serverFirstCarte = usersCartes.get('server')[0]
    for user in usersCartes.keys() :
        if user != 'server' :
            writerr = adr_writer.get(user)[1]
            carte_joueur = usersCartes.get(user)
            writerr.write(f"""la carte du distributeur est {serverFirstCarte} \n Vos cartes sont : 
            {carte_joueur} et ils valent {calculValeurTotal(carte_joueur)}\r\n""".encode())

    await jouerParties(party)


    
async def jouerParties(party):
    usersCartes = partiesInProgress.get(party)# On recupere les cartes des joueurs
    partyCartes = partiesInProgressCartes.get(party)# On recupere les cartes de la partie

    # La condition d'arret de la partie
    while len(usersCartes)>1:
        for user in list(usersCartes.keys())[1:]:
            writerr = adr_writer.get(user)[1]
            choice = await continueTirage(user,".\r\n")
            while choice:   #le serveur demande au joueur s'il souhaite une carte supplémentaire;
                    userCartes = usersCartes.get(user) # On recupere la liste des cartes du joueur courant
                    randCarte = partyCartes[random.randrange(0,len(partyCartes))] # On prend une carte au hazard dans les cartes de la partie
                    partyCartes.remove(randCarte) # On retire la carte distribue au joueur courant
                    
                    userCartes.append(randCarte) # On ajoute la carte tirer sur la liste des cartes du joueur
                    usersCartes.update({user:userCartes}) # On met a jour les cartes du joueur dans le dictionnaire de sa partie
                    
                    writerr = adr_writer.get(user)[1]
                    writerr.write(f"Vos cartes sont : {userCartes} et ils valent {calculValeurTotal(userCartes)}\r\n".encode()) # On envoie au joueur la liste de ses cartes

                    if joueurPerdu(userCartes):#Si le joueur à tirer plus de 21
                        writerr.write(f"Tu a perdu, attend le resultat de la partie.\r\n".encode())
                        choice = False
                    else :
                        choice = await continueTirage(user,".\r\n") # On redemande au joueur s'il veut jouer
                        
                    userCartes = usersCartes.get(user) # On recupere la liste des cartes du joueur courant
                    writerr.write(f"Vos cartes sont : {userCartes} et ils valent {calculValeurTotal(userCartes)}\r\n".encode())

            # On retire le joueur ayant decide de ne plus tirer de cartes de la liste des joueurs de la partie en cours 
            # apres l'avoir ajoute dans la liste des joueurs en attente de resultat pour ne pas le donner des cartes
            if party in endPartiesUsers.keys():
                users = endPartiesUsers.get(party)
                userCartes = usersCartes.get(user)
                users.append((user,userCartes))
                endPartiesUsers.update({party:users})
                usersCartes.pop(user) # On a d'abord besoin des points du joueur a faire
                
            else :
                endPartiesUsers[party]=[(user,userCartes)]
                usersCartes.pop(user)
                

    
    
    serverCartes=usersCartes.get("server")   #au tour du serveur
    
    while calculValeurTotal(serverCartes)<17:
        carte = partyCartes[random.randrange(0, len(partyCartes))]
        serverCartes.append(carte)
        partyCartes.remove(carte) # On retire la carte attribue au server de la liste des cartes de la partie courante
    usersCartes.update({'server':serverCartes})

    users = endPartiesUsers.get(party)
    serverCartes = usersCartes.get('server')
    users.append(('server',serverCartes))
    endPartiesUsers.update({party:users})


    partiesInProgressCartes.update({party:partyCartes}) # On met a jour les cartes de la partie

    await resultat(party)

async def resultat(party):#en cours difficulté au niveau de l'affichage du résultat
    max=0
    #vainqueur=[] # Pourquoi il devrait y avoir plusieurs vainqueur ?
    vainqueur=''
    # La variable usersCartes est a revoir car les utilisateurs sont supprimes
    usersCartes = endPartiesUsers.get(party)# On recupere le dictionnaire liant les cartes et joueurs
    for userCartes in usersCartes:#calcul de la valeur max de la partie
        user = userCartes[0]
        cartes = userCartes[1]
        if max<calculValeurTotal(cartes) and calculValeurTotal(cartes)<=21: # J'ai change la condition
            max=calculValeurTotal(cartes)
            vainqueur=user

    if max>0:
        for userCartes in usersCartes:
            user = userCartes[0]
            cartes = userCartes[1]
        
            if vainqueur==user:
                if user!='server':
                    writerr = adr_writer.get(user)[1]
                    writerr.write(f"Vous avez gagner avec {max} points \r\n".encode())
                    writerr.write("END\r\n".encode())
                else :
                    print(f"Vous etes le gagnant avec {max} points")
            else:
                if user!='server':
                    writerr = adr_writer.get(user)[1]
                    writerr.write(f"""Vous etes perdant avec {calculValeurTotal(cartes)} points 
                    contre {max} pour {vainqueur}\r\n""".encode())
                    writerr.write("END\r\n".encode())
                else :
                    print(f"""Vous etes perdant avec {calculValeurTotal(cartes)} contre {max} pour {vainqueur}""")
    else :
        for userCartes in usersCartes:
            user = userCartes[0]
            cartes = userCartes[1]
            if user!='server':
                writerr = adr_writer.get(user)[1]
                writerr.write(f"""Il n'y a aucun gagnat. Vous etes tous plus de 21 points.\n 
                Les votres sont {calculValeurTotal(cartes)}\r\n""".encode())
                writerr.write("END\r\n".encode())
            else :
                print(f"""Il n'y a aucun gagnat. Vous etes tous plus de 21 points.\n 
                Les votres sont {calculValeurTotal(cartes)}\r\n""")
            

#le joueur demande une carte ou s'arrête;
async def continueTirage(user,msg):    
    inputOutput = adr_writer.get(user) 
    writerr = inputOutput[1]            # RAJOUTER "MORE"

    #on demande si le joueur veux tirer une carte
    writerr.write(msg.encode())

    #on recupere la reponse du joueur
    readerr=inputOutput[0]
    data=await readerr.readline()
    res=int(data.decode()[5:])

    return res==1
                

# Calcul la valeur des cartes d'un jooueur
def calculValeurTotal(cartes):
    res=0
    asCartes=0
    for i in range(len(cartes)):
        carte = cartes[i]
        if carte in ('valet','dame','roi'): 
            res+=10
        elif carte in ('2','3','4','5','6','7','8','9','10') :
            res+=int(carte)
        else : # Si la carte recupere n'est ni un valet, ni un roi, ni une dame et ni un chiffre, on incremente le nombre de as
            asCartes+=1
    
    for i in range(asCartes):
        if res+11>=21:
            res+=1
        else :
            res+=11
    
    return res

def joueurPerdu(cartesJoueur):
    res=calculValeurTotal(cartesJoueur)
    if(res>21):
        return True
    else:
        return False



async def handle_request_croupier(reader, writer):
    addr = writer.get_extra_info('peername')[0]
    msg = f"Bienvenue User {addr} \n"

    writer.write(msg.encode())
    await writer.drain()

    data1 = await reader.readline()
    taille1 = len(data1)-2
    table = data1[5:taille1].decode()
    msg1 = f"La table {table} est cree \n"
    print(msg1)
    writer.write(msg1.encode())
    await writer.drain()

    data2 = await reader.readline()
    taille2=len(data2)-2
    temps = int(data2[5:taille2].decode())

    tables[table]=temps

    msg2 = f"Le temps d'attente pour la table {table} est de {temps} et il est ajoute a la liste\n"
    print(msg2)

    writer.write(msg2.encode())
    await writer.drain()

    writer.close()




async def blackjack_server():
    # start a socket client server
    server_client = await asyncio.start_server(handle_request_joueur, '0.0.0.0', 667)
    addr_client = server_client.sockets[0].getsockname()
    # start a socket croupier server
    server_croupier = await asyncio.start_server(handle_request_croupier, '0.0.0.0', 668)
    addr_croupier = server_croupier.sockets[0].getsockname()

    print(f'Serving on {addr_croupier} for croupier and {addr_client} for client')

    async with server_client:
        await server_client.serve_forever() # handle requests for ever

    async with server_croupier:
        await server_croupier.serve_forever() # handle requests for ever

if __name__ == '__main__':
    asyncio.run(blackjack_server())
