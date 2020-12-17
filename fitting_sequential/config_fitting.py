# config_fitting.py
"""
A file to contain input parameters for fitting functions
"""

import numpy as np
from scipy.special import erf

# Import values from paircounting config file
import config
import numpy as np
path = config.path

boxsize = config.boxsize

r_bin_edges = config.r_bin_edges

mass_bin_edges = config.mass_bin_edges

num_sat_parts = config.num_sat_parts

run_label = config.run_label


# Parameters to include in the fit
# Each element represents a parameter of the HOD
# A 1 means that parameter is being fitted.
# A 0 means that parameter is fixed and the value from the relevant text file is being used
# In order the parameters are Mmin, sigma_logM, M0, M1, alpha
# The position of the next line affects the sequential fitting batch script! Keep it at 31 if possible!
included_params = [1,1,1,1,1]
mm_flag = included_params[0]
si_flag = included_params[1]
m0_flag = included_params[2]
m1_flag = included_params[3]
al_flag = included_params[4]

# Sometimes a parameter's position in the parameter array can change
# Create a variable to track where a parameter's value lies in the array
mm_index = None
si_index = None
m0_index = None
m1_index = None
al_index = None


param_index_tracker = 0
if mm_flag==1:
    mm_index = param_index_tracker
    param_index_tracker += 1
if si_flag==1:
    si_index = param_index_tracker
    param_index_tracker += 1
if m0_flag==1:
    m0_index = param_index_tracker
    param_index_tracker += 1
if m1_flag==1:
    m1_index = param_index_tracker
    param_index_tracker += 1
if al_flag==1:
    al_index = param_index_tracker
    param_index_tracker += 1


# Number of steps to take with each emcee walker
num_steps = 5000

# Number of walkers to use in the emcee fitting 
num_walkers = 20

# Run label for paircounting so the results can be read in
# Could make this dynamic so it used run label from above
run_path = "/cosma7/data/durham/dc-grov1/Halo_mass_pair_binning/BGS/reduced_catalog/FastHodFitting/fitting/FastHodFitting/paircounting/red_cat_correct"

# Include cen and sat HOD definitions in here as they can change when fitting different things
def spline_kernel_integral(x):
    """
    Returns the integral of the unscaled spline kernel function from -1 to x
    """
    if hasattr(x, "__len__"):
        # x in an array
        integral = np.zeros(len(x))
        absx = abs(x)
        ind = absx < 0.5
        integral[ind] = absx[ind] - 2*absx[ind]**3 + 1.5*absx[ind]**4
        ind = np.logical_and(absx >= 0.5, absx < 1.)
        integral[ind] = 0.375 - 0.5*(1-absx[ind])**4
        ind = absx >= 1.
        integral[ind] = 0.375
        ind = x < 0
        integral[ind] = -integral[ind]
    else:
        # x is a number
        absx = abs(x)
        if   absx < 0.5: integral = absx - 2*absx**3 + 1.5*absx**4
        elif absx < 1:   integral = 0.375 - 0.5*(1-absx)**4
        else:            integral = 0.375
        if x < 0: integral = -integral
    return integral

def cumulative_spline_kernel(x, mean=0, sig=1):
    """
    Returns the integral of the rescaled spline kernel function from -inf to x.
    The spline kernel is rescaled to have the specified mean and standard
    deviation, and is normalized.
    """
    integral = spline_kernel_integral((x-mean)/(sig*np.sqrt(12))) / 0.75
    y = 0.5 * (1. + 2*integral)
    return y

# Now change Cen_HOD definition

def Cen_HOD(params,mass_bins,Mmin,sigma_logM):
    # Fixed values are used if the flags =0
    if mm_flag == 1:
        Mmin = params[mm_index]
    if si_flag ==1:
        sigma_logM = params[si_index]
    result = cumulative_spline_kernel(np.log10(mass_bins), mean = Mmin, sig=sigma_logM/np.sqrt(2))
    return(result)

def Sat_HOD(params,cen_hod,mass_bins,M0,M1,alpha):
    if m0_flag == 1:
        M0 = params[m0_index]
    if m1_flag ==1:
        M1 = params[m1_index]
    if al_flag == 1:
        alpha = params[al_index]
    
    M0 = 10**M0
    M1 = 10**M1

    result = cen_hod * (((mass_bins-M0)/M1)**alpha)
    return(result)

# Likelihood definition can change a lot between fits as well 

def likelihood_calc(model,y,err):
    # Here take a constant fractional error and exclude BAO scale
    likelihood = - 0.5 * (np.sum((1 - (model[:75] / y[:75]))**2) / err**2)
    return likelihood
    
# target_2pcf contains the target correlation functions to fit to
# Rescale this by the cosmology factor here:
cosmo_factor = np.genfromtxt("cosmology_rescaling_factor.txt")
target_2pcf = np.genfromtxt("/cosma7/data/durham/dc-grov1/Halo_mass_pair_binning/BGS/xi_r_mxxl.dat")
for i in range(10):
    target_2pcf[:,i] = target_2pcf[:,i] * cosmo_factor

# Target number density array
target_num_den = np.genfromtxt("/cosma7/data/durham/dc-grov1/Halo_mass_pair_binning/BGS/target_number_density.dat")

# error to apply to each point on the correlation function, can affect the speed of the fitting and walkers
# can get stuck in local minima if this is set too small (<0.1) 
err = 0.7

# Number density error parameter, affects how tight the target number density constraint is
num_den_err = 0.01**0.5

# Positions of the priors on the parameters for fitting

# Priors are now variable depending on which parameters are being fitted and which are fixed

num_params = np.sum(included_params)
priors = np.zeros((num_params,2))
if mm_flag == 1:
    priors[mm_index,0] = 11
    priors[mm_index,1] = 16
if si_flag == 1:
    priors[si_index,0] = 0
    priors[si_index,1] = 4
if m0_flag == 1:
    priors[m0_index,0] = 8
    priors[m0_index,1] = 14
if m1_flag == 1:
    priors[m1_index,0] = 11
    priors[m1_index,1] = 17
if al_flag == 1:
    priors[al_index,0] = 0
    priors[al_index,1] = 4


# Flag to change whether initial parameters are in random locations across the prior space or not
##### Don't change this for sequential fitting
initial_params_random = False

# If initial_params_random = False then use initial parameters close to these values:
# For sequential fitting we need to change how walker parameters are initialised
initial_params = np.zeros(num_params)
if mm_flag == 1:
    initial_params[mm_index] = 12
if si_flag == 1:
    initial_params[si_index] = 0.1
if m0_flag == 1:
    initial_params[m0_index] = 10.
if m1_flag == 1:
    initial_params[m1_index] = 13.
if al_flag == 1:
    initial_params[al_index] = 0.9


num_mass_bins_big = 20000


random_seed = 10

save_path = "fits_sequential_test_2"

print(mm_index,si_index,m0_index,m1_index,al_index)

print(priors)

print(initial_params)
