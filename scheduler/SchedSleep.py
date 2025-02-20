"""
This scheduler is a FCFS sleeper one :
- Released jobs are pushed in the back of one single queue
- Two jobs cannot be executed on the same machine at the same time
- Only the job at the head of the queue can be allocated

  - If the job is too big (will never fit the machine), it is rejected
  - If the job can fit the machine now, it is allocated (and run) instantly
  - If the job cannot fit the machine now

    - If the job cannot fit because of other jobs, the unused machines are switched OFF
    - Else (if the job cannot fit because of sleeping machines), those machines are switched ON

Let us assume all machines have the following pstates (corresponding to file
energy_platform_homogeneous.xml)
"""

from batsim.batsim import BatsimScheduler

import sys
from sortedcontainers import SortedSet
from enum import Enum
from procset import ProcSet


class PState(Enum):
    ComputeFast = 0
    ComputeMedium = 1
    ComputeSlow = 2
    Sleep = 13
    SwitchingOFF = 14
    SwitchingON = 15


class State(Enum):
    Computing = 0
    Idle = 1
    Sleeping = 2
    SwitchingON = 3
    SwitchingOFF = 4


class SchedSleep(BatsimScheduler):

    def onAfterBatsimInit(self):
        self.nb_completed_jobs = 0

        self.jobs_completed = []
        self.jobs_waiting = []

        self.sched_delay = 0.0

        #temps pour que les machines s'eteingnent, 0 = infini
        self.sleep_wait = 0
        # pourcentage max de machine en idle
        self.max_Idle = 0.25
        #Rallume des machines si le nombre de machine en idle est inférieur au max
        self.boot_Idle = True
        #tableau qui stock les requestcall pour éviter de lancer deux requestcall au même timestamp
        self.requestCall = SortedSet()
        #est-ce que le workload est fini
        self.end_Workload = False
        #tableau qui stock a quel timestamp la machine i doit s'arreter, si pas d'arret programmer la machine i est à -1
        self.machine_wait = [-1] * self.bs.nb_resources

        self.open_jobs = []

        self.computing_machines = SortedSet()
        self.idle_machines = SortedSet(range(self.bs.nb_resources))
        self.sleeping_machines = SortedSet()
        self.switching_ON_machines = SortedSet()
        self.switching_OFF_machines = SortedSet()

        self.machines_states = {
            int(i): State.Idle.value for i in range(self.bs.nb_resources)}
        print("machines_states", self.machines_states)



        print("machines_waiter", self.machine_wait)




    def scheduleJobs(self):
        """print('\n\n\n\n')
        print('open_jobs = ', self.open_jobs)

        print('computingM = ', self.computing_machines)
        print('idleM = ', self.idle_machines)
        print('sleepingM = ', self.sleeping_machines)
        print('switchingON_M = ', self.switching_ON_machines)
        print('switchingOFF_M = ', self.switching_OFF_machines)"""

        scheduled_jobs = []
        pstates_to_change = []
        loop = True

        # If there is a job to schedule
        while loop and self.open_jobs:
            job = self.open_jobs[0]
            nb_res_req = job.requested_resources

            if nb_res_req > self.bs.nb_resources:  # Job too big -> rejection
                sys.exit("Rejection unimplemented")

            # Job fits now -> allocation
            elif nb_res_req <= len(self.idle_machines):
                res = ProcSet(*self.idle_machines[:nb_res_req])
                job.allocation = res
                scheduled_jobs.append(job)
                for r in res:  # Machines' states update
                    self.machine_wait[r]=-1 #on remet le compteur à 0 puisqu'on affecte une tache à la machine
                    self.idle_machines.remove(r)
                    self.computing_machines.add(r)
                    self.machines_states[r] = State.Computing.value
                self.open_jobs.remove(job)

            else:  # Job can fit on the machine, but not now
                loop = False
                #print("############ Job does not fit now ############")
                nb_not_computing_machines = self.bs.nb_resources - \
                    len(self.computing_machines)
                #print("nb_res_req = ", nb_res_req)
                #print("nb_not_computing_machines = ",
                #      nb_not_computing_machines)
                if nb_res_req <= nb_not_computing_machines:  # The job could fit if more machines were switched ON
                    # Let us switch some machines ON in order to run the job
                    nb_res_to_switch_ON = nb_res_req - \
                        len(self.idle_machines) - \
                        len(self.switching_ON_machines)
                    #print("nb_res_to_switch_ON = ", nb_res_to_switch_ON)
                    if nb_res_to_switch_ON > 0:  # if some machines need to be switched ON now
                        nb_switch_ON = min(
                            nb_res_to_switch_ON, len(self.sleeping_machines))
                        if nb_switch_ON > 0:  # If some machines can be switched ON now
                            res = self.sleeping_machines[:nb_switch_ON]
                            for r in res:  # Machines' states update + pstate change request
                                self.sleeping_machines.remove(r)
                                self.switching_ON_machines.add(r)
                                self.machines_states[
                                    r] = State.SwitchingON.value
                                pstates_to_change.append(
                                    (PState.ComputeFast.value, (r, r)))
                else:  # The job cannot fit now because of other jobs
                    # Let us put all idle machines to sleep
                    pstates_to_change = self.SleepMachineControl()


        # if there is nothing to do, let us put all idle machines to sleep
        if not self.open_jobs:
            pstates_to_change = self.SleepMachineControl()

        """
        if not self.open_jobs:
            for r in self.idle_machines:
                self.switching_OFF_machines.add(r)
                self.machines_states[r] = State.SwitchingOFF.value
                pstates_to_change.append((PState.Sleep.value, (r, r)))
            self.idle_machines = SortedSet()
        """

        # update time
        self.bs.consume_time(self.sched_delay)

        #print(self.bs.time())

        #On récupère le temps du prochain éteignage et si il a pas déjà été programmer
        #on envoit un message à batsim pour nous reveiller à ce moment la 
        if max(self.machine_wait)==-1:
            nextSleep=-1
        else:
            nextSleep = min(filter(lambda i: i > 0, self.machine_wait))
            if not(nextSleep in self.requestCall):
                self.bs.wake_me_up_at(nextSleep)
                self.requestCall.add(nextSleep)
                #print(self.machine_wait, nextSleep)



        # send to uds
        self.bs.execute_jobs(scheduled_jobs)
        for (val, (r1,r2)) in pstates_to_change:
            self.bs.set_resource_state(ProcSet(r1), val)


    def SleepMachineControl(self):
        pstates_to_change = []

        #nombre de machine en idle actuellement
        nb_idle_machine = len(self.idle_machines)
        for r in self.idle_machines.copy():
            #si la machine n'a pas de temps d'arret programmé
            if self.machine_wait[r]<0:
                #si le nombre de machine en idle est supérieur au nombre max
                #ou qu'on est arrivé à la fin du workload
                #on programme la l'arret de la machine imédiatement
                if (nb_idle_machine > self.bs.nb_resources * self.max_Idle or self.end_Workload):
                    self.machine_wait[r]=round(self.bs.time())-1 #arret immédiat
                    nb_idle_machine-=1
                #Sinon si sleep_wait n'est pas égal à 0 on programme l'arret dans sleep_wait
                elif self.sleep_wait !=0:
                    self.machine_wait[r]=round(self.bs.time()) + self.sleep_wait #arret retardé
            #Si la machine à un temps d'arret programmé et qu'il est inférrieur au temps actuelle alors on l'eteint
            if self.machine_wait[r]>0 and self.machine_wait[r]<=round(self.bs.time()):
                self.idle_machines.remove(r)
                self.machine_wait[r]=-1
                self.switching_OFF_machines.add(r)
                self.machines_states[r] = State.SwitchingOFF.value
                pstates_to_change.append((PState.Sleep.value, (r, r)))


        #Si le workload est pas fini et qu'on a boot_Idle à vrai
        if not(self.end_Workload) and self.boot_Idle:
            #On récupère le nombre de machine qu'on a besoin d'allumé
            nb_need_switch_on =round(self.bs.nb_resources * self.max_Idle - len(self.idle_machines) - len(self.switching_ON_machines))
            if nb_need_switch_on > 0:
                #on prend le minimun entre le nombre de machine eteinte et ce qu'on a besoin
                nb_switch_ON = min(
                    nb_need_switch_on, len(self.sleeping_machines))
                #Si on a au moins une machine à allumer
                if nb_switch_ON > 0:
                    res = self.sleeping_machines[0:nb_switch_ON]
                    #on parcours les machines et on les allume
                    for r in res:
                        self.sleeping_machines.remove(r)
                        self.switching_ON_machines.add(r)
                        self.machines_states[
                            r] = State.SwitchingON.value
                        pstates_to_change.append(
                            (PState.ComputeFast.value, (r, r)))

        return pstates_to_change

    def onNoMoreJobsInWorkloads(self):
        pstates_to_change = []
        self.end_Workload = True

        for r in self.idle_machines:
            self.idle_machines.remove(r)
            self.machine_wait[r]=-1
            self.switching_OFF_machines.add(r)
            self.machines_states[r] = State.SwitchingOFF.value
            pstates_to_change.append((PState.Sleep.value, (r, r)))

        for (val, (r1,r2)) in pstates_to_change:
            self.bs.set_resource_state(ProcSet(r1), val)

    def onRequestedCall(self):
        #print("request call, time:",self.bs.time())

        #print(self.idle_machines)
        pstates_to_change = self.SleepMachineControl()

        if max(self.machine_wait)==-1:
            nextSleep=-1
        else:
            nextSleep = min(filter(lambda i: i > 0,      self.machine_wait))
            if not(nextSleep in self.requestCall):
                self.bs.wake_me_up_at(nextSleep)
                self.requestCall.add(nextSleep)
            #print(self.machine_wait, nextSleep)

        for (val, (r1,r2)) in pstates_to_change:
            self.bs.set_resource_state(ProcSet(r1), val)

    def onJobSubmission(self, job):
        #print("job:",job)
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job]) # This job requests more resources than the machine has
        else:
            self.open_jobs.append(job)
            self.scheduleJobs()

    def onJobCompletion(self, job):
        for res in job.allocation:
            self.idle_machines.add(res)
            self.computing_machines.remove(res)
            self.machines_states[res] = State.Idle.value
        self.scheduleJobs()

    def onMachinePStateChanged(self, machines, new_pstate):
        machine = machines[0]
        if (int(new_pstate) == PState.ComputeFast.value) or (new_pstate == PState.ComputeMedium.value) or (int(new_pstate) == PState.ComputeSlow.value):  # switched to a compute pstate
            if self.machines_states[machine] == State.SwitchingON.value:
                self.switching_ON_machines.remove(machine)
                self.idle_machines.add(machine)
                self.machines_states[machine] = State.Idle.value
            else:
                sys.exit(
                    "Unhandled case: a machine switched to a compute pstate but was not switching ON")
        elif int(new_pstate) == PState.Sleep.value:
            if self.machines_states[machine] == State.SwitchingOFF.value:
                self.switching_OFF_machines.remove(machine)
                self.sleeping_machines.add(machine)
                self.machines_states[machine] = State.Sleeping.value
            else:
                sys.exit(
                    "Unhandled case: a machine switched to a sleep pstate but was not switching OFF")
        else:
            #print(new_pstate,PState.Sleep.value, new_pstate==PState.Sleep.value)
            sys.exit("Switched to an unhandled pstate: " + str(new_pstate))

        self.scheduleJobs()
