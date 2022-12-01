#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Multi-layer perceptron
# Copyright (C) 2011  Nicolas P. Rougier
#
# Distributed under the terms of the BSD License.
# -----------------------------------------------------------------------------
import numpy as np
import math

def sigmoid(x):
    ''' Sigmoid like function using tanh '''
    # return np.tanh(x)
    temp = np.zeros(np.shape(x))
    for row in range(len(x)):
        temp[row] = (1 / (1 + math.exp(-x[row]))) * 2 - 1
    return temp

class MLP:
    ''' Multi-layer perceptron class. '''

    def __init__(self, *args):
        ''' Initialization of the perceptron with given sizes.  '''

        self.shape = args
        n = len(self.shape[0])

        # Build layers
        self.layers = []
        # Input layer (+1 unit for bias)
        
        print(self.shape[0])
        
        self.layers.append(np.ones(self.shape[0][0]+1))
        # Hidden layer(s) + output layer
        for i in range(1,n):
            self.layers.append(np.ones(self.shape[0][i]))

        # Build weights matrix 
        self.weights = []
        for i in range(n-1):
            self.weights.append(np.zeros((self.layers[i].size,
                                         self.layers[i+1].size)))                                                             
            
    def propagate_forward(self, data):
        ''' Propagate data from input layer to output layer. '''

        # Set input layer
        self.layers[0][0:-1] = data

        # Propagate from layer 0 to layer n-1 using sigmoid as activation function
        for i in range(1,len(self.shape[0])):
            # Propagate activity
            self.layers[i][...] = sigmoid(np.dot(self.layers[i-1],self.weights[i-1]))

        # Return output
        return self.layers[-1]