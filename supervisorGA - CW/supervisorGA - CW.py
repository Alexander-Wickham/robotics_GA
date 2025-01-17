from controller import Supervisor
from controller import Keyboard
from controller import Display

import numpy as np
import ga,os,sys,struct,random

class SupervisorGA:
    def __init__(self):
        # Simulation Parameters
        # Please, do not change these parameters
        self.time_step = 32 # ms
        self.time_experiment = 60 # s
        
        # Initiate Supervisor Module
        self.supervisor = Supervisor()
        # Check if the robot node exists in the current world file
        self.robot_node = self.supervisor.getFromDef("Controller")
        if self.robot_node is None:
            sys.stderr.write("No DEF Controller node found in the current world file\n")
            sys.exit(1)
        # Get the robots translation and rotation current parameters    
        self.trans_field = self.robot_node.getField("translation")  
        self.rot_field = self.robot_node.getField("rotation")
        
        # Check Receiver and Emitter are enabled
        self.emitter = self.supervisor.getDevice("emitter")
        self.receiver = self.supervisor.getDevice("receiver")
        self.receiver.enable(self.time_step)
        
        # Initialize the receiver and emitter data to null
        self.receivedData = "" 
        self.receivedWeights = "" 
        self.receivedFitness = "" 
        self.emitterData = ""
        
        ### Define here the GA Parameters
        self.num_generations = 100
        self.num_population = 100
        self.num_elite = 10
        
        # size of the genotype variable
        self.num_weights = 0
        
        # Creating the initial population
        self.population = []
        
        # All Genotypes
        self.genotypes = []
        
        # Display: screen to plot the fitness values of the best individual and the average of the entire population
        self.display = self.supervisor.getDevice("display")
        self.width = self.display.getWidth()
        self.height = self.display.getHeight()
        self.prev_best_fitness = 0.0
        self.prev_average_fitness = 0.0
        self.display.drawText("Fitness (Best - Red)", 0,0)
        self.display.drawText("Fitness (Average - Green)", 0,10)
        
        # Black mark
        self.mark_node = self.supervisor.getFromDef("Mark")
        if self.mark_node is None:
            sys.stderr.write("No DEF Mark node found in the current world file\n")
            sys.exit(1)
        self.mark_trans_field = self.mark_node.getField("translation")
        
        self.crashed = False

    def createRandomPopulation(self):
        # Wait until the supervisor receives the size of the genotypes (number of weights)
        if(self.num_weights > 0):
            # Define the size of the population
            pop_size = (self.num_population,self.num_weights)
            # Create the initial population with random weights
            self.population = np.random.uniform(low=-1.0, high=1.0, size=pop_size)

    def handle_receiver(self):
        while(self.receiver.getQueueLength() > 0):
            self.receivedData = self.receiver.getData().decode("utf-8")
            typeMessage = self.receivedData[0:7]
            # Check Message 
            if(typeMessage == "weights"):
                self.receivedWeights = self.receivedData[9:len(self.receivedData)] 
                self.num_weights = int(self.receivedWeights)
            elif(typeMessage == "fitness"):  
                self.receivedFitness = float(self.receivedData[9:len(self.receivedData)])
            elif(typeMessage == "crashed"):
                self.crashed = True
            self.receiver.nextPacket()
        
    def handle_emitter(self):
        if(self.num_weights > 0):
            # Send genotype of an individual
            string_message = str(self.emitterData)
            string_message = string_message.encode("utf-8")
            # print("Supervisor send:", string_message)
            self.emitter.send(string_message)     
        
    def run_seconds(self,seconds,target,demo):
        #print("Run Simulation")
        right = [0.97, 0.14, 0.14, -1.59]
        left = [-0.49, 0.61, 0.61, 2.23]

        stop = int((seconds*1000)/self.time_step)
        iterations = 0
        self.handle_emitter()
        self.emitterData = self.emitterData[0:-2]
        while self.supervisor.step(self.time_step) != -1:
            self.handle_emitter()
            self.handle_receiver()
            if not demo:
                pos = self.robot_node.getField("translation").getSFVec3f()
                rot = self.robot_node.getField("rotation").getSFRotation()
                
                b = True
                
                for (r, rig, lef) in zip(rot, right, left):
                    if r < rig or r > lef:
                        b = False
                
                if b:
                    self.receivedFitness = float(-50)
                    break
                
                if target[0] > 0:
                    if pos[0] > target[0]:
                        self.receivedFitness = float(100) - iterations
                        self.crashed = False
                        break
                    elif pos[0] < -target[0]:
                        self.receivedFitness = float(-50) - iterations
                        self.crashed = False
                        break
                else:
                    if pos[0] < target[0]:
                        self.receivedFitness = float(100) - iterations
                        self.crashed = False
                        break
                    elif pos[0] > -target[0]:
                        self.receivedFitness = float(-50) - iterations
                        self.crashed = False
                        break
                
                if self.crashed:
                    self.receivedFitness = float(-100)
                    self.crashed = False
                    break
            if(stop == iterations):
                self.crashed = False
                # self.receivedFitness = float(-10) - iterations
                break
            iterations = iterations + 1
                
    def evaluate_genotype(self,genotype,generation):
        # Here you can choose how many times the current individual will interact with both environments
        # At each interaction loop, one trial on each environment will be performed
        numberofInteractionLoops = 1
        currentInteraction = 0
        fitnessPerTrial = []
        while currentInteraction < numberofInteractionLoops:
            #######################################
            # TRIAL: TURN RIGHT
            #######################################
            # Send genotype to robot for evaluation
            self.emitterData = str(genotype) + ' or'
            
            # Reset robot position and physics
            INITIAL_TRANS = [0.007, 0, 0.35]
            self.trans_field.setSFVec3f(INITIAL_TRANS)
            INITIAL_ROT = [-0.5, 0.5, 0.5, 2.09]
            self.rot_field.setSFRotation(INITIAL_ROT)
            self.robot_node.resetPhysics()
            
            # Reset the black mark position and physics
            INITIAL_TRANS = [0.01, -0.03425, 0.193]
            self.mark_trans_field.setSFVec3f(INITIAL_TRANS)
            self.mark_node.resetPhysics()
        
            # Evaluation genotype 
            self.run_seconds(self.time_experiment, [0.2, 0, -0.15], False)
        
            # Measure fitness
            fitness = self.receivedFitness
            
            # Check for Reward and add it to the fitness value here
            # Add your code here

            curr_pos = self.robot_node.getField("translation")
            curr_trans = curr_pos.getSFVec3f()
            
            
            # fitness += 100 * ((-0.15 - curr_trans[2]) ** 2 + (-0.35 - curr_trans[0]) ** 2) ** 0.5
            
            fitness -= 100 * ((-0.15 - curr_trans[2]) ** 2 + (0.35 - curr_trans[0]) ** 2) ** 0.5
            
            fitness += 100 * (0.4 - curr_trans[2])
            
            
            # fitness
            
            print("Fitness: {}".format(fitness))     
                        
            # Add fitness value to the vector
            fitnessPerTrial.append(fitness)
                        
            #######################################
            # TRIAL: TURN LEFT
            #######################################
            # Send genotype to robot for evaluation
            self.emitterData = str(genotype) + ' or'
            
            # Reset robot position and physics
            INITIAL_TRANS = [0.007, 0, 0.35]
            self.trans_field.setSFVec3f(INITIAL_TRANS)
            INITIAL_ROT = [-0.5, 0.5, 0.5, 2.09]
            self.rot_field.setSFRotation(INITIAL_ROT)
            self.robot_node.resetPhysics()
            
            # Reset the black mark position and physics
            INITIAL_TRANS = [0.01, -0.1, 0.193]
            self.mark_trans_field.setSFVec3f(INITIAL_TRANS)
            self.mark_node.resetPhysics()
        
            # Evaluation genotype 
            self.run_seconds(self.time_experiment, [-0.2, 0, -0.15], False)
        
            # Measure fitness
            fitness = self.receivedFitness
            
            # Check for Reward and add it to the fitness value here
            # Add your code here

            curr_pos = self.robot_node.getField("translation")
            curr_trans = curr_pos.getSFVec3f()


            # fitness += 100 * ((-0.15 - curr_trans[2]) ** 2 + (0.35 - curr_trans[0]) ** 2) ** 0.5
            
            fitness -= 100 * ((-0.15 - curr_trans[2]) ** 2 + (-0.35 - curr_trans[0]) ** 2) ** 0.5
            
            fitness += 100 * (0.4 - curr_trans[2])


            print("Fitness: {}".format(fitness))
            
            # Add fitness value to the vector
            fitnessPerTrial.append(fitness)
            
            # End 
            currentInteraction += 1
            
        print(fitnessPerTrial)    
        
        fitness = np.mean(fitnessPerTrial)
        current = (genotype,fitness)
        self.genotypes.append(current)  
        
        return fitness

    def run_demo(self):
        # Read File
        genotype = np.load("Best_1.npy")
        # test = np.load("Best.npy")
        print(genotype)
        # print(test)
        # Turn Left
        
        # Send Genotype to controller
        self.emitterData = str(genotype) + ' dr'
        
        # Reset robot position and physics
        INITIAL_TRANS = [0.007, 0, 0.35]
        self.trans_field.setSFVec3f(INITIAL_TRANS)
        INITIAL_ROT = [-0.5, 0.5, 0.5, 2.09]
        self.rot_field.setSFRotation(INITIAL_ROT)
        self.robot_node.resetPhysics()
        
        # Reset the black mark position and physics
        INITIAL_TRANS = [0.01, -0.1, 0.193]
        self.mark_trans_field.setSFVec3f(INITIAL_TRANS)
        self.mark_node.resetPhysics()
    
        # Evaluation genotype 
        self.run_seconds(self.time_experiment, [-0.2, 0, -0.15], True) 
        
        # Measure fitness
        fitness = self.receivedFitness
        print("Fitness without reward or penalty: {}".format(fitness))
        
        # Turn Right
        
        # Send Genotype to controller
        self.emitterData = str(genotype) + ' dr'
        
        # Reset robot position and physics
        INITIAL_TRANS = [0.007, 0, 0.35]
        self.trans_field.setSFVec3f(INITIAL_TRANS)
        INITIAL_ROT = [-0.5, 0.5, 0.5, 2.09]
        self.rot_field.setSFRotation(INITIAL_ROT)
        self.robot_node.resetPhysics()
        
        # Reset the black mark position and physics
        INITIAL_TRANS = [0.01, -0.03425, 0.193]
        self.mark_trans_field.setSFVec3f(INITIAL_TRANS)
        self.mark_node.resetPhysics()
    
        # Evaluation genotype 
        self.run_seconds(self.time_experiment, [0.2, 0, -0.15], True)  
        
        # Measure fitness
        fitness = self.receivedFitness
        print("Fitness without reward or penalty: {}".format(fitness))    
    
    def run_optimization(self):
        # Wait until the number of weights is updated
        while(self.num_weights == 0):
            self.handle_receiver()
            self.createRandomPopulation()
        
        print("starting GA optimization ...\n")
        
        # For each Generation
        for generation in range(self.num_generations):
            print("Generation: {}".format(generation))
            current_population = []   
            # Select each Genotype or Individual
            for population in range(self.num_population):
                genotype = self.population[population]
                # Evaluate
                fitness = self.evaluate_genotype(genotype,generation)
                #print(fitness)
                # Save its fitness valuegeneration
                current_population.append((genotype,float(fitness)))
                #print(current_population)
                
            # After checking the fitness value of all indivuals
            # Save genotype of the best individual
            # best = ga.getBestGenotype(current_population)
            best = ga.getBestGenotype(self.genotypes)
            average = ga.getAverageGenotype(current_population)
            
            for x in range(len(best[0])):
                best[0][x] = np.format_float_positional(best[0][x], trim='-')
            
            np.save("Best_1.npy",best[0])
            print(best[0])
            self.plot_fitness(generation, best[1], average)
            
            # Generate the new population using genetic operators
            if (generation < self.num_generations - 1):
                # self.genotypes.sort(key=lambda g: g[1], reverse=False)
                # temp = self.genotypes[-self.num_population:]
                # temp = random.choices(self.genotypes, k=self.num_population)
                # self.genotypes = temp
                # print(temp)
                # self.population = ga.population_reproduce(temp,self.num_elite)
                self.population = ga.population_reproduce(current_population,self.num_elite)
        
        #print("All Genotypes: {}".format(self.genotypes))
        print("GA optimization terminated.\n")   
    
    
    def draw_scaled_line(self, generation, y1, y2): 
        # Define the scale of the fitness plot
        XSCALE = int(self.width/self.num_generations)
        YSCALE = 100
        self.display.drawLine((generation-1)*XSCALE, self.height-int(y1*YSCALE), generation*XSCALE, self.height-int(y2*YSCALE))
    
    def plot_fitness(self, generation, best_fitness, average_fitness):
        if (generation > 0):
            self.display.setColor(0xff0000)  # red
            self.draw_scaled_line(generation, self.prev_best_fitness, best_fitness)
    
            self.display.setColor(0x00ff00)  # green
            self.draw_scaled_line(generation, self.prev_average_fitness, average_fitness)
    
        self.prev_best_fitness = best_fitness
        self.prev_average_fitness = average_fitness
  
    
if __name__ == "__main__":
    # Call Supervisor function to initiate the supervisor module   
    gaModel = SupervisorGA()
    
    # Function used to run the best individual or the GA
    keyboard = Keyboard()
    keyboard.enable(50)
    
    # Interface
    print("(R|r)un Best Individual or (S|s)earch for New Best Individual:")
    while gaModel.supervisor.step(gaModel.time_step) != -1:
        resp = keyboard.getKey()
        if(resp == 83 or resp == 65619):
            gaModel.run_optimization()
            print('s', "(R|r)un Best Individual or (S|s)earch for New Best Individual:")
        elif(resp == 82 or resp == 65619):
            gaModel.run_demo()
            print('r', "(R|r)un Best Individual or (S|s)earch for New Best Individual:")
        
