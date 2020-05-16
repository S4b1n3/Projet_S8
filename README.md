# Projet_S8
Depot contenant toutes les ressources utiles/nécessaires à la réalisation du projet

## Notebook
Workload_Generator.ipynb :
Permet de générer un workload directement depuis les fichiers de google.

statistique.ipynb : 
Permet soit de générer un CSV où chaque ligne représente une tache, on ne garde que le temps du démarage, la longueur et la ressource demandée de la tache. Ensuite on peut load ce csv pour faire différentes statistiques. On peut aussi charger un workload si besoin.

output_analysis.ipynb:
Un premier affichage des sorties de batsim. Contient aussi quelques commandes utiles.

## Scheduler
On est partis du scheduler "fcfsSchedSleep.py" de pybatsim qu'on a modifié et qui est disponible sous le nom de "SchedSleep.py".
Il y a pas de fichier de configuration les paramètres sont donc à changer dans le fichier directement.
Les deux paramètres qu'il est possible de modifier sont: 
- self.sleep_wait : le temps d'attente avant que la machine ne s'éteigne, si la valeur est à 0 alors la machine ne s'éteindra jamais.
- self.max_Idle : pourcentage ( [0:1] ) de machine à garder en idle au maximum.
- self.boot_Idle : si cette variable est à vrai alors le scheduler va rallumer des machines si on a moins du nombre maximum de machine en idle.

L'implémentation de la gestion des machines en idle a été faite dans la fonction SleepMachineControl(). Le principe est d'affecter à chaque machine en idle une heure à laquelle elles vont devoir s'éteindre si elles n'ont pas déjà une heure programmée. Cette information est stockée dans le tableau self.machine_wait. Si la machine est re-afectée à une tache entre temps on réinitialise ce temps à -1. Si le temps est dépassé alors on éteint la machine. Pour que le scheduler puisse êteindre la machine au moment exact où elle doit s'éteindre on envoie à batsim un Request_Call avec l'heure de la prochaine extinction, Afin que batsim nous rêveille à ce moment t.

Par rapport au scheduler de base nous avons rajouté aussi le fait que les machines vont automatiquement s'éteindre si le workload est fini puisque aucune nouvelle tache va venir se rajouter.

## Platforme
La platforme c'est ce qui permet de charactérisé le réseau de machine du datacenter simulé. Nous avons gardé la platform "cluster_energy_128.xml" de batsim avec ses valeurs. C'est un réseau de 128 machines avec 15 états, même si nous en n'utilisons que 4. Idle/Computing sur un état, allumage, extinction et éteint (respectivement 0, 13, 14, 15). Dans "watt_per_state" il y a la consomation d'electricité, à gauche des ':' c'est en idle et à droite c'est en computing. C'est une platforme avec 128 machiens alors le workload a été adapté afin de correspondre à ce nombre de machineq.

## Quelques commandes
- **batsim -p platforms/cluster_energy_test.xml -w workloads/workload_energy.json -e ./output/ -E** pour lancer une simulation coté batsim
- **pybatsim scheduler/SchedSleep.py** pour lancer le scheduler
- **./evalys-master/examples/poquetm/plot_energy_info.py --gantt -j output/_jobs.csv -p output/_pstate_changes.csv --off 13 --switchon '-1' --switchoff '-2'** pour afficher le gantt du scheduling
- **./evalys-master/examples/poquetm/plot_energy_info.py --gantt -j output/_jobs.csv -p output/_pstate_changes.csv --off 13 --switchon '-1' --switchoff '-2' --ru -m output/_machine_states.csv -e output/_consumed_energy.csv --power**  pour afficher l'ensemble complet de graphique d'analyse
- **./evalys-master/examples/poquetm/plot_energy_info.py -e output/_consumed_energy_normal.csv output/_consumed_energy_moyenne.csv  --names 'normal' 'moyenne' --power --energy** pour comparer deux consommations d'energie 
