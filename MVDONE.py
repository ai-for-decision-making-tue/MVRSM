### MVDONE uses a piece-wise linear surrogate model for optimization of
### expensive cost functions with mixed-integer variables.
###
### MVDONE_minimize(obj, x0, lb, ub, num_int, max_evals, rand_evals) solves the minimization problem
###
### min f(x)
### st. lb<=x<=ub, the first num_int variables of x are integer
###
### where obj is the objective function, x0 the initial guess,
### lb and ub are the bounds, num_int is the number of integer variables,
### and max_evals is the maximum number of objective evaluations (rand_evals of these
### are random evaluations).
###
### Laurens Bliek, 06-03-2019

import os
import math
import random
import time
import numpy as np

from scipy.optimize import minimize, Bounds

def MVDONE_minimize(obj, x0, lb, ub, num_int, max_evals, rand_evals=0):
	d = len(x0) # dimension, number of variables
	current_time = time.time() # time when starting the algorithm
	next_X = [] # candidate solution presented by the algorithm
	
	## Initialize the surrogate model
	def initializeModel():
		next_X = np.copy(x0)
		
		def ReLU(x): # Rectified Linear Unit
			temp = np.copy(x)
			for i, xx in enumerate(x):
				temp[i] = [max(0,xx[0])]
			return np.asarray(temp)
		

		def ReLUderiv(x): # Derivative of Rectified Linear Unit
			temp = np.copy(x)
			for i, xx in enumerate(x):
				temp[i] = [0.5*(xx[0]==0) + (xx[0]>0)]
			return np.asarray(temp)
		
		# Define basis functions Z=ReLU(W*x+B)
		W = [] # Basis function weights
		B = [] # Basis function bias
		
		# Add a constant basis function independent on the variable x, giving the model an offset
		W.append([0]*d)
		B.append([1])
		
		# Add basis functions dependent on one integer variable
		for k in range(num_int): 
			for i in range(int(lb[k]),int(ub[k])+1):
				if i == lb[k]:
					temp = [0]*d
					temp[k] = 1
					W.append(np.copy(temp))
					B.append([-i])
				elif i == ub[k]:
					temp = [0]*d
					temp[k] = -1
					W.append(np.copy(temp))
					B.append([i])
				else:
					temp = [0]*d
					temp[k] = -1
					W.append(np.copy(temp))
					B.append([i])
					temp = [0]*d
					temp[k] = 1
					W.append(np.copy(temp))
					B.append([-i])
					
		# Add basis functions dependent on two subsequent integer variables
		for k in range(1,num_int): 
			for i in range(int(lb[k])-int(ub[k-1]),int(ub[k])-int(lb[k-1])+1):
				if i == lb[k]-ub[k-1]:
					temp = [0]*d
					temp[k] = 1
					temp[k-1] = -1
					W.append(np.copy(temp))
					B.append([-i])
				elif i == ub[k]-lb[k-1]:
					temp = [0]*d
					temp[k] = -1
					temp[k-1] = 1
					W.append(np.copy(temp))
					B.append([i])
				else:
					temp = [0]*d
					temp[k] = -1
					temp[k-1] = 1
					W.append(np.copy(temp))
					B.append([i])
					temp = [0]*d
					temp[k] = 1
					temp[k-1] = -1
					W.append(np.copy(temp))
					B.append([-i])
		
		num_discr_basisfunctions = len(B)-1 #number of basis functions only related to the discrete variables
		
		# Add dx random linearly independent basis functions (and parallel ones)
		# which depend on both integer and continuous variables,
		# where dx is the number of continuous variables
		dx = d-num_int
		tempW = np.random.random((dx,d))
		tempW = (2*tempW-1)/d #normalize between -1/d and 1/d		
		for k in range(dx):
			
			
			#Check for the range in which B needs to lie by moving orthogonal to W
			
			#print(W)
			signs = np.sign(tempW[k,:])
			#print(signs)
			#input('hoi')
			
				
			# Find relevant corner points of the [lb, ub] hypercube
			cornerpoint1 = np.copy(lb)
			cornerpoint2 = np.copy(ub)
			for j in range(d):
				if signs[j]<0:
					cornerpoint1[j] = ub[j]
					cornerpoint2[j] = lb[j]
			#print('cornerpoint1', cornerpoint1)
			#print('cornerpoint2', cornerpoint2)
			#input('hoi2')
			
			# Calculate minimal distance from hyperplane to corner points
			b1 = np.dot(tempW[k,:],cornerpoint1)
			b2 = np.dot(tempW[k,:],cornerpoint2)
			
			if b1>b2:
				print('Warning: b1>b2. This may lead to problems.')
			
			#add around 10*d of these basis functions in total, of which dx are linearly independent and the rest are parallel
			#for j in range(math.ceil(10*d/float(d-num_int))):
			#or add the same number of basis functions as for the discrete variables
			for j in range(math.ceil(num_discr_basisfunctions/num_int)):
			#or just add 1000 of them
			#for j in range(500):
				#print(math.ceil(10*d/float(d-num_int)))
				b = (b2-b1)*np.random.random()+b1
				W.append(np.copy(tempW[k,:]))
				B.append([-float(b)])
				
		
			
			#print('W', W)
			#print('B', B)
			#input('hoi3')
			
			
			
			
			
		
		W = np.asarray(W)	
		B = np.asarray(B)	
		
		# print('W has shape ', np.shape(W))
		# print('B has shape ', np.shape(B))
		# input(',,,')
		# import matplotlib.pyplot as plt
		#plt.imshow(np.concatenate((W, B), axis=1), aspect=0.05)
		# plt.imshow(W, aspect=0.05)
		# plt.colorbar()
		# plt.show()
		
		# Transform input into model basis functions Z=ReLU(W*x+B)
		def Z(x): 
			x = np.asarray(x)
			x = x.reshape(-1,1)
			temp = np.matmul(W,x)
			temp = temp + B
			temp = np.asarray(temp)
			Zx = ReLU(temp)
			return Zx
		
		# Derivative of basis functions w.r.t. x
		def Zderiv(x):
			x = np.asarray(x)
			x = x.reshape(-1,1)
			temp = np.matmul(W,x)
			temp = temp +B
			temp = np.asarray(temp)
			dZx = ReLUderiv(temp)
			return dZx
		
		D = len(B) # Number of basis functions
		c = np.zeros((D,1)) # Model weights, to be trained with recursive least squares (RLS)
		for i in range( 1, num_discr_basisfunctions):
			c[i] = 1 # model weights start out as 1 for the discrete basis functions to stimulate convexity
		reg = 1e-8 # Regularization parameter. 1e-8 is good for the noiseless case, change to something like 1e-3 if there is noise.
		P = np.diag(np.ones(D))/reg # RLS covariance matrix
		model = {'W':W, 'B':B, 'ReLU':ReLU, 'ReLUderiv':ReLUderiv, 'Z':Z, 'Zderiv':Zderiv, 'D':D, 'c':c, 'reg':reg, 'P':P} # Store model variables in a dictionary
		
		return next_X, model
	
	## Update the model when a new data point (x,y) comes in
	def updateModel(x,y, model): 
		Zx = model['Z'](x)			
		# Recursive least squares algorithm
		temp = np.matmul(model['P'], Zx)
		g = temp/(1+np.matmul(np.transpose(Zx),temp))
		model['P'] = model['P'] - np.matmul(g, np.transpose(temp))
		model['c'] = model['c'] + ( y-np.matmul( np.transpose(Zx), model['c'] ) ) * g # Only here, output y is used (to update the model weights)
				
		# Define model output for any new input x2
		def out(x2):
			return np.matmul( np.transpose(model['c']), model['Z'](x2) ).item(0,0)
		# Define model output derivative for any new input x2 (used in the optimization step)
		def deriv(x2):
			c = np.transpose(model['c'])			
			temp = np.reshape(model['Zderiv'](x2),(model['Zderiv'](x2)).shape[0])
			temp = np.matmul(np.diag(temp), model['W'])
			result = np.transpose(np.matmul( c, temp  ))
			return result

		model['out'] = out
		model['outderiv'] = deriv
		return model
	
	
	
	### Start actual algorithm
	next_X, model = initializeModel()
	best_X = np.copy(next_X) # Best candidate solution found so far
	best_y = 9999999 # Best objective function value found so far
	
	## Iteratively evaluate the objective, update the model, find the minimum of the model, and explore the search space
	time_start1 = time.time()
	for ii in range(0,max_evals):
		print(f"Starting MVDONE iteration {ii}/{max_evals}")
		x = np.copy(next_X).astype(float)
		if ii==0:
			y = obj(x) # Evaluate the objective
			
			# Scale with respect to initial y value, causing the optimum to lie below 0.
			# This is better for exploitation and prevents the algorithm from getting stuck at the boundary.
			y0 = y
			def scale(y):
				if abs(y0)>1e-8:
					y = (y-y0)/abs(y0)
				else:
					y = (y-y0)
				return y
			def inv_scale(y):
				if abs(y0)>1e-8:
					y = y*abs(y0)+y0
				else:
					y = y+y0
				return y
			model['inv_scale'] = inv_scale		
			y = scale(y)
		else:
			y = scale(obj(x)) # Evaluate the objective and scale it
		
		
		# Keep track of the best found objective value and candidate solution so far
		if y < best_y:
			best_X = np.copy(x)
			best_y = y
			
			
		## Update the surrogate model
		time_start = time.time() 
		model = updateModel(x,y, model)
		update_time = time.time()-time_start # Time used to update the model
		
		## Minimization of the surrogate model
		time_start = time.time()
		temp = minimize(model['out'], best_X, method='L-BFGS-B', bounds = Bounds(lb, ub), jac=model['outderiv'], options={'maxiter':20,'maxfun':20})
		minimization_time = time.time()-time_start # Time used to find the minimum of the model
		next_X = np.copy(temp.x)
		#print('minimum of surrogate: ', next_X)
		next_X_before_rounding = np.copy(next_X)
		for j in range(num_int):
					next_X[j] = np.round(next_X[j]) # Round integer variables to nearest integer point
					#next_X = [int(x) for x in next_X]
	
		
		
		
		
		## Visualize model
		
		# if ii > max_evals/2:
			
			# import matplotlib.pyplot as plt
			# # print('Hoi', len(xxxx))
			# # print(len(toplot))
			# # plt.plot(xxxx,toplot)
			# # #plt.plot(jjjj,toplot[iiii],'*')
			# # titlestr = ['Dimension ', iiii]
			# # plt.title(titlestr)
			# # plt.show()
			
			
			# from mpl_toolkits.mplot3d import Axes3D
			# from matplotlib import cm
			# from matplotlib.ticker import LinearLocator, FormatStrFormatter
			# #XX = np.arange(next_X[0]-0.5, next_X[0]+0.5, 0.01)
			# #XX = np.arange(lb[0], ub[0], 0.05)
			# #YY = np.arange(lb[1], ub[1], 0.05)
			# XX = np.arange(-2, 4, 0.05)
			# YY = np.arange(-2, 4, 0.05)
			# XXX, YYY = np.meshgrid(XX, YY)
			# R = []
			# for XXXX in XX:
				# temp = []
				# for YYYY in YY:
					# #print(next_X)
					# temp.append(model['out']([XXXX,YYYY]))
				# R.append(temp)
			# R = np.copy(R)
			
			# fig = plt.figure()
			# ax = fig.gca(projection='3d')
			# surf = ax.plot_surface(XXX, YYY, R, cmap=cm.coolwarm,
				   # linewidth=0, antialiased=False)
			# fig.colorbar(surf, shrink=0.5, aspect=5)
			# plt.show()
		
		
	
		
		# Just to be sure, clip to the bounds
		np.clip(next_X, lb, ub)
		
		# Check if minimizer really gives better result
		#if model['out'](next_X) > model['out'](x) + 1e-8:
			#print('Warning: minimization of the surrogate model in MVDONE yielded a worse solution, maybe something went wrong.')
		
		## Exploration step (else the algorithm gets stuck in the local minimum of the surrogate model)
		next_X_before_exploration = np.copy(next_X)
		next_X = np.copy(next_X)
		if ii<max_evals-2: # Skip exploration before the last iteration, to end at the exact minimum of the surrogate model.
			# Discrete exploration
			for j in range(0,num_int):
				r = random.random()
				r2 = random.random() # Used to choose whether to explore left or right
				a = next_X[j]
				prob = 1/d # Probability for each variable to increase or decrease
				while r < prob:
					if a==lb[j] and a<ub[j]: 
						a += 1 # Explore to the right
					elif a==ub[j] and a>lb[j]:
						a -= 1 # Explore to the left
					elif a>lb[j] and a<ub[j]:
						if r2<0.5:
							a += 1
						else:
							a -= 1
					r = r*2
				next_X[j]=a
			# Continuous exploration
			for j in range(num_int, d):
				r = np.random.normal()*(ub[j]-lb[j])*0.1*1/(math.sqrt(d)) #choose a variance that scales inversely with the total number of variables
				a = next_X[j]
				while a+r>ub[j] or a+r<lb[j]:
					r = np.random.normal()*(ub[j]-lb[j])*0.1*1/(math.sqrt(d)) #out of bounds so repeat
				a += r
				next_X[j]=a
					
			
		#print('Exploration: from ', next_X_before_exploration, 'to ', next_X)
		
		
		# Just to be sure, clip to the bounds again
		np.clip(next_X, lb, ub)		


		# For the first few iterations, just do random search instead (overwrites next_X)
		if ii<rand_evals: 
			next_X[0:num_int] = np.round(np.random.rand(num_int)*(ub[0:num_int]-lb[0:num_int]) + lb[0:num_int]) # Random guess (integer)
			next_X[num_int:d] = np.random.rand(d-num_int)*(ub[num_int:d]-lb[num_int:d]) + lb[num_int:d] # Random guess (continuous)

		time_per_iteration = time.time() - time_start1
		
		# Save data to log file
		filename = 'log_MVDONE_'+ str(current_time) + ".log"
		with open(filename, 'a') as f:
			print('\n\n MVDONE iteration: ', ii, file=f)
			print('Time spent training the model:				 ', update_time, file=f)
			print('Time spent finding the minimum of the model: ', minimization_time, file=f)
			print('Total computation time for this iteration:	', time_per_iteration, file=f)
			print('Current time: ', time.time(), file=f)
			print('Evaluated data point and evaluation:						   ', np.copy(x).astype(float),	 ', ',	inv_scale(y), file=f)
			print('Predicted value at evaluated data point (after learning)       ', np.copy(x).astype(float), ', ', inv_scale(model['out'](x)), file=f) 
			print('Best found data point and evaluation so far:				   ', np.copy(best_X).astype(float),	', ',  inv_scale(best_y), file=f)
			print('Best data point according to the model and predicted value:	   ', next_X_before_rounding, ', ', inv_scale(model['out'](next_X_before_rounding)), file=f)
			print('Best rounded	 point according to the model and predicted value:', next_X_before_exploration, ', ', inv_scale(model['out'](next_X_before_exploration)), file=f)
			print('Suggested next data point and predicted value:				   ', next_X,	', ',  inv_scale(model['out'](next_X)), file=f)
			if ii>=max_evals-1:
				np.set_printoptions(threshold=np.inf)
				print('Model c parameters: ', np.transpose(model['c']), file=f)
				print('Model W parameters: ', np.transpose(model['W']), file=f)
				print('Model B parameters: ', np.transpose(model['B']), file=f)
				np.set_printoptions(threshold=1000)
	
		time_start1 = time.time()
		
	return best_X, inv_scale(best_y), model, filename


# Read data from log file (this reads the best found objective values at each iteration)
def read_log(filename):
	with open(filename,'r') as f:
			MVDONEfile = f.readlines()
			MVDONE_best = []
			for i, lines in enumerate(MVDONEfile):
				searchterm = 'Best data point according to the model and predicted value'
				if searchterm in lines:
					#print('Hello', MVDONEfile)
					temp = MVDONEfile[i-1]
					temp = temp.split('] , ')
					temp = temp[1]
					MVDONE_best.append(float(temp))
	return MVDONE_best

# Plot the best found objective values at each iteration
def plot_results(filename):
	import matplotlib.pyplot as plt
	fig = plt.figure(1)
	MVDONE_ev=read_log(filename)
	plt.plot(MVDONE_ev)
	plt.xlabel('Iteration')
	plt.ylabel('Objective')
	plt.grid()
	plt.show()
	#fig.show()
	
def visualise_model(model, obj, x0, lb, ub, num_int):
	## Plot in 'one dimension' (first integer and first continuous variable)
	#print(num_int)
	#print(ub[num_int]-lb[num_int])
	#print((ub[num_int]-lb[num_int])/0.05)
	print('W parameters: ', model['W'])
	print('B parameters: ', model['B'])
	int_range = np.arange(lb[0],ub[0],0.05) #range of the integer variable
	cont_range = np.arange(lb[num_int],ub[num_int],0.05) #range of the continuous variable
	model_output = np.zeros((len(int_range),len(cont_range)))
	obj_output = np.zeros((len(int_range),len(cont_range)))
	x = np.copy(x0) #For the other variables, use x0 as the value
	correctint = 999
	for i in range(len(int_range)):
		x[0] = int_range[i]
		if abs(x[0]+10) <=0.05:
				correctint = i
		for j in range(len(cont_range)):
			x[num_int] = cont_range[j]
			model_output[i,j] = model['inv_scale'](model['out'](x))
			obj_output[i,j] = obj(x)
	X, Y = np.meshgrid(int_range, cont_range)
	R = np.sqrt(X**2 + Y**2)
	R = np.sin(R)
	#print(R.shape)
	#print(model_output.shape)
	import matplotlib.pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D	
	from matplotlib import cm	
	fig = plt.figure(2)
	ax = fig.add_subplot(121, projection='3d')
	ax.plot_surface(X, Y, np.transpose(model_output),cmap=cm.coolwarm)
	ax.set_title('Model output')
	ax.set_xlabel('Discrete variable')
	ax.set_ylabel('Continuous variable')
	ax2 = fig.add_subplot(122, projection='3d')
	ax2.plot_surface(X, Y, np.transpose(obj_output),cmap=cm.coolwarm)
	ax2.set_title('Function output')
	ax2.set_xlabel('Discrete variable')
	ax2.set_ylabel('Continuous variable')
	fig.show()
	
	
	
	
	fig2 = plt.figure(3)
	ax3 = fig2.add_subplot(121)
	ax3.plot(cont_range, np.transpose(model_output[correctint,:]))
	ax3.set_title('Model output')
	#ax3.set_xlabel('Discrete variable')
	ax3.set_xlabel('Continuous variable')
	ax4 = fig2.add_subplot(122)
	ax4.plot(cont_range, np.transpose(obj_output[correctint,:]))
	ax4.set_title('Function output')
	ax4.set_xlabel('Continuous variable')
	fig2.show()
	
	
	
	
	
	
	
	plt.show()
	
	
	
	
	# fig2 = plt.figure()
	# ax3 = fig2.add_subplot(121)
	# cs3 = ax3.contourf(X, Y, np.transpose(model_output),cmap=cm.coolwarm)
	# ax3.contour(cs3)
	# ax3.set_title('Model output')
	# ax3.set_xlabel('Discrete variable')
	# ax3.set_ylabel('Continuous variable')
	# ax4 = fig2.add_subplot(122)
	# cs4 = ax4.contourf(X, Y, np.transpose(obj_output),cmap=cm.coolwarm)
	# ax4.contour(cs4)
	# ax4.set_title('Function output')
	# ax4.set_xlabel('Discrete variable')
	# ax4.set_ylabel('Continuous variable')
	# plt.show()
			
			