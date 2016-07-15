from datetime import datetime
import sys

import pandas as pd
import numpy as np

import math
from math import exp, sqrt, log

from IPython import embed

# Plotting
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

# =================   OU PROCESS   =================

# MC params
np.random.seed(2000)  # set the seed
dt = 1  # time step
M = 1000  # no. of time steps

# Model params:
mu = 10
sigma = 0.3

Y_t1 = np.zeros((M + 1))
Y_t2 = np.zeros((M + 1))
Y_t3 = np.zeros((M + 1))

Y_t1[0] = -50.0
Y_t2[0] = 50.0
Y_t3[0] = 0.0

theta1 = 0.003
theta2 = 0.01
theta3 = 0.1

for i in xrange(1, M + 1, 1):
    Y_t1[i] = Y_t1[i-1] + theta1 * (mu - Y_t1[i-1]) * dt + sigma * math.sqrt(dt) * np.random.normal(0, 1)
    Y_t2[i] = Y_t2[i-1] + theta2 * (mu - Y_t2[i-1]) * dt + sigma * math.sqrt(dt) * np.random.normal(0, 1)
    Y_t3[i] = Y_t3[i-1] + theta3 * (mu - Y_t3[i-1]) * dt + sigma * math.sqrt(dt) * np.random.normal(0, 1)

# Y_t = pd.Series(index=range(M), data=Y_t)
Y_t1 = pd.Series(Y_t1, name='Y_t1')
Y_t2 = pd.Series(Y_t2, name='Y_t2')
Y_t3 = pd.Series(Y_t3, name='Y_t3')

# =================   MULTIVARIATE REGRESSION   =================

# Main refs used:
# http://www.ats.ucla.edu/stat/sca/finn/finn4.pdf
# CQF_January_2016_M4S11_Annotated.pdf
# http://statsmodels.sourceforge.net/stable/_modules/statsmodels/tsa/ar_model.html#AR

from statsmodels.tsa.tsatools import (lagmat, add_trend)
# from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.ar_model import AR


def dof_resid(exog=None, nobs=None, my_dof=None):
    if my_dof is None:
        rank = np.ndim(exog)
        dof = nobs - rank
    else:
        dof = my_dof
    return dof

def my_OLS(Y, X, dof=None):
    """
    Linear Regression implementation using Ordinary Least Squares (OLS) results
    :param Y: endogenous (dependent) variables
    :param X: exogenous (independent) variables
    :param dof: degrees of freedom
    :return: dictionary with regression results

    See ref: http://statsmodels.sourceforge.net/devel/_modules/statsmodels/regression/linear_model.html#OLS
    """

    # Get estimates for beta coefficients using result beta_hat = [(X'X)^-1]X'Y
    G = np.linalg.inv(np.dot(X.T, X))  # [(X'X)^-1] term, aka variance-covariance factor
    beta_hat = np.dot(G, np.dot(X.T, Y))

    # Get estimates for epsilon residuals using result resid_hat = Y - X*beta_hat
    resid_hat = Y - np.dot(X, beta_hat)

    # Get t-statistics for the ADF using result tvalue = beta_hat / bse, where bse is the standard error of beta_hat
    # Note: must first estimate the standard error using result sqrt(diag[kron(G, ols_scale)]) where:
    # G: as above
    # ols_scale: the unbiased estimate of the residuals covariance (scaled by the degrees of freedom - dof)
    # kron: kronecker product
    # diag: diagonal elements
    # See ref above or p.29 in  for more info

    nobs = len(resid_hat)  # number of observations

    # The residual degree of freedom, defined as the number of observations minus the rank of the regressor matrix
    if dof is None:  # if degrees of freedom not specified, then set to number of observations in resid_hat
        dof = dof_resid(exog=X, nobs=nobs)
    else:
        dof = dof_resid(my_dof=dof)

    ssr = np.dot(resid_hat, resid_hat.T)  # ee' term
    ols_scale = ssr / dof  # ee' term must be scaled by dof to obtain unbiased estimate
    cov_params = np.kron(G, ols_scale)  # covariance matrix of parameters
    bvar = np.diag(cov_params)  # entries on the diagonal of the covariance matrix  are the variances
    bse = np.sqrt(bvar)  # must take square root to get standard error
    tvalue = beta_hat / bse  # t-statistic for a given parameter estimate

    dic = {
        'beta_hat': beta_hat,
        'resid_hat': resid_hat,
        'nobs': nobs,
        'dof': dof,
        'ssr': ssr,
        'ols_scale': ols_scale,
        'cov_params': cov_params,
        'bse': bse,
        'tvalue': tvalue
           }

    return dic


def my_AR(endog, maxlag, trend=None):
    """
    Autoregressive model implementation, aka AR(p)
    :param endog: the dependent variables
    :param maxlag: maximum number of lags to use
    :param trend: 'c': add constant, 'nc' or None: no constant
    :return: my_OLS dictionary

    See ref: http://statsmodels.sourceforge.net/stable/_modules/statsmodels/tsa/ar_model.html#AR
    """
    # Dependent data matrix
    Y = endog[maxlag:]  # has observations for the fit p lags removed
    # Explanatory data matrix
    X = lagmat(endog, maxlag, trim='both')
    if trend is not None:
        X = add_trend(X, prepend=True, trend=trend)  # prepends puts trend column at the beginning

    # Get degrees of freedom
    nobs = len(resid_hat)  # number of observations
    k_ar = maxlag  # number of lags used, which affects number of observations
    k_trend = 0  # the number of trend terms included 'nc'=0, 'c'=1
    dof_AR = nobs - k_ar - k_trend  # degrees of freedom

    return my_OLS(Y, X, dof=dof_AR)


# =================   ADF TEST   =================
y = Y_t1.head(10)
maxlag = 1

y = np.asarray(y)
# nobs = y.shape[0]
ydiff = np.diff(y)  # get the differences (dY_t)

ydall = lagmat(ydiff[:, None], maxlag, trim='both', original='in')  # get the diff lags specified (dY_t-k terms)
nobs = ydall.shape[0]  # number of observations
ydall[:, 0] = y[-nobs - 1:-1]  # replace 0 ydiff with level of y

ydshort = ydiff[-nobs:]

Y = ydshort
X = ydall[:, :maxlag + 1]

k_ar = maxlag
k_trend = 1
# dof = nobs - k_ar - k_trend  # degrees of freedom
my_result = my_OLS(Y, X)

from statsmodels.tsa.stattools import adfuller
py_result = adfuller(x=y, maxlag=1, regression='nc', autolag=None, regresults=True)

sys.exit()

print py_result[3].resols.bse
s = py_result[3].resols.scale  # the scale used in the cov_params function
# my_OLS(Y, X, dof=6) == py_result[3].resols.cov_params() == py_result[3].resols.cov_params(scale=s)
# py_result[3].resols.scale should be == my_result['ols_scale']

# =================   COMPARE MY AR(p) VS STATSMODELS   =================

endog = Y_t1.head(10)
maxlag = 3

my_result = my_AR(endog=endog, maxlag=maxlag)

# Compare to statsmodels AR(p) model using 'cmle' (conditional maximum likelihood estimation (default method)
fit = AR(np.array(endog)).fit(maxlag=maxlag, trend='nc')  # use only specified lags and remove constant from models

# Print fitted params and residuals of model, should be equivalent (or very close) to estimates above
print "\
AR.fit.params={0} \n MY beta_hat={1} \n\
AR.fit.resid={2} \n MY resid_hat={3} \n\
AR.fit.nobs={4} \n MY nobs={5} \n\
AR.fit.cov_params(scale=ols_scale)={6} \n MY cov_params={7} \n\
AR.fit.bse={8} \n MY bse={9} \n\
AR.fit.tvalues={10} \n MY tvalue={11} \n\
".format(
    fit.params, my_result['beta_hat'],
    fit.resid, np.array(my_result['resid_hat']),
    fit.nobs, my_result['nobs'],
    fit.cov_params(scale=ols_scale), my_result['cov_params'],
    fit.bse, my_result['bse'],
    fit.tvalues, my_result['tvalue']
)





