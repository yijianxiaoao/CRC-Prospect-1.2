# -*- coding: utf-8 -*-
"""
Statistical methods implemented without SciPy for easy deployment.

"Includes chi-square tests, t-tests (normal approximation), odds ratios and 95% confidence intervals, logistic and Probit regression, average marginal effects, and standardized regression coefficients.
"""
import math

import numpy as np


# ---------------------------------------------------------------------------
# Chi-square test
# ---------------------------------------------------------------------------

def _gamma_lower(a: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(a, x) using a series or continued fraction. """
    if x <= 0:
        return 0.0
    if x < a + 1:
        term = 1.0 / a
        total = term
        for n in range(1, 300):
            term *= x / (a + n)
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # Find the continuous fraction Q(a, x)
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 300):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1 - q


def chi2_p_value(chi2: float, df: int) -> float:
    """Chi-square test p-value. """
    if df <= 0 or chi2 <= 0:
        return 1.0
    return max(0.0, min(1.0, 1 - _gamma_lower(df / 2.0, chi2 / 2.0)))


def chi_square(table) -> tuple:
    """
    Chi-square test.

    :param table: Two-dimensional contingency table (list of list)
    :return: (chi2, df, p)
    """
    arr = np.asarray(table, dtype=float)
    if arr.ndim != 2 or arr.sum() == 0:
        return 0.0, 0, 1.0
    total = arr.sum()
    row = arr.sum(axis=1, keepdims=True)
    col = arr.sum(axis=0, keepdims=True)
    expected = row @ col / total
    with np.errstate(divide='ignore', invalid='ignore'):
        chi2 = np.nansum((arr - expected) ** 2 / np.where(expected == 0, np.nan, expected))
    df = (arr.shape[0] - 1) * (arr.shape[1] - 1)
    return float(chi2), int(df), chi2_p_value(float(chi2), int(df))


# ---------------------------------------------------------------------------
# t-test (normal approximation for large samples) and correlation
# ---------------------------------------------------------------------------

def p_from_z(z: float) -> float:
    """Two-sided p-value using the normal approximation, suitable for large samples. """
    return math.erfc(abs(z) / math.sqrt(2))


def t_test(group_a, group_b) -> dict:
    """Compare two group means using Welch t-test; for large samples, the p-value is approximated by the normal distribution. """
    a = np.asarray([x for x in group_a if x is not None], dtype=float)
    b = np.asarray([x for x in group_b if x is not None], dtype=float)
    if len(a) < 2 or len(b) < 2:
        return {'mean_a': float(a.mean()) if len(a) else 0,
                'mean_b': float(b.mean()) if len(b) else 0,
                't': 0.0, 'p': 1.0, 'diff': 0.0}
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / len(a) + vb / len(b))
    t = (a.mean() - b.mean()) / se if se > 0 else 0.0
    return {'mean_a': round(float(a.mean()), 3), 'mean_b': round(float(b.mean()), 3),
            'diff': round(float(a.mean() - b.mean()), 3),
            't': round(float(t), 3), 'p': round(p_from_z(t), 4)}


def pearson(x, y) -> float:
    """Pearson correlation coefficient. """
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    if len(a) < 2 or a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ---------------------------------------------------------------------------
# Odds ratio (OR)
# ---------------------------------------------------------------------------

def odds_ratio(a: int, b: int, c: int, d: int) -> dict:
    """
    Calculate the odds ratio and its 95% confidence interval.

    :param a: Exposed group · Positive outcome
    :param b: Exposed group · Negative outcome
    :param c: Control group · Positive outcome
    :param d: Control group · Negative outcome
    :return: {'or', 'ci_low', 'ci_high'}
    """
    a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5      # Haldane Adjusted, Avoid division by zero
    or_value = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    log_or = math.log(or_value)
    return {
        'or': round(or_value, 3),
        'ci_low': round(math.exp(log_or - 1.96 * se), 3),
        'ci_high': round(math.exp(log_or + 1.96 * se), 3),
    }


# ---------------------------------------------------------------------------
# Path analysis (Standardized regression coefficient)
# ---------------------------------------------------------------------------

def standardized_regression(X, y) -> dict:
    """
    Standardized multiple regression, Path Coefficients for Path Analysis.

    :param X: Independent-variable matrix (n x k)
    :param y: Dependent-variable vector (n)
    :return: {'beta': [...], 'r2': coefficient of determination, 'n': Sample size}
    """
    arr_x = np.asarray(X, dtype=float)
    arr_y = np.asarray(y, dtype=float)
    if arr_x.ndim == 1:
        arr_x = arr_x.reshape(-1, 1)
    if len(arr_y) < 3:
        return {'beta': [0.0] * arr_x.shape[1], 'r2': 0.0, 'n': len(arr_y)}

    # Standardization
    x_std = arr_x.std(axis=0)
    x_std[x_std == 0] = 1
    xz = (arr_x - arr_x.mean(axis=0)) / x_std
    y_std = arr_y.std() or 1
    yz = (arr_y - arr_y.mean()) / y_std

    design = np.column_stack([np.ones(len(xz)), xz])
    beta, *_ = np.linalg.lstsq(design, yz, rcond=None)
    y_hat = design @ beta
    ss_res = float(((yz - y_hat) ** 2).sum())
    ss_tot = float(((yz - yz.mean()) ** 2).sum()) or 1.0
    return {
        'beta': [round(float(b), 3) for b in beta[1:]],
        'intercept': round(float(beta[0]), 3),
        'r2': round(1 - ss_res / ss_tot, 3),
        'n': int(len(arr_y)),
    }

# ===========================================================================
# Multivariate analysis: Logistic Return (IRLS Iterative Weighted Least Squares)
# ===========================================================================

def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def logistic_regression(X, y, feature_names=None, max_iter: int = 200,
                        tol: float = 1e-8, l2: float = 0.0) -> dict:
    """
    Binary Logistic Return (Maximum likelihood estimation).

    :param X: Independent-variable matrix (n x k)
    :param y: Binary dependent variable (0/1)
    :param feature_names: Independent-variable name
    :return: {'features': [...], 'coef': [...], 'or': [...], 'ci_low': [...],
              'ci_high': [...], 'p': [...], 'aic', 'bic', 'n', 'loglik', 'converged'}
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    yv = np.asarray(y, dtype=float)
    n, k = arr.shape
    names = list(feature_names or ['x%d' % (i + 1) for i in range(k)])

    design = np.column_stack([np.ones(n), arr])
    beta = np.zeros(k + 1)
    converged = False
    cov = None

    for _ in range(max_iter):
        eta = design @ beta
        p = _sigmoid(eta)
        w = np.clip(p * (1 - p), 1e-10, None)
        hess = design.T @ (design * w[:, None])
        grad = design.T @ (yv - p)
        if l2 > 0:                      # L2 Punishment (Excluding the intercept)
            penalty = np.eye(k + 1) * l2
            penalty[0, 0] = 0.0
            hess = hess + penalty
            grad = grad - penalty @ beta
        try:
            delta = np.linalg.solve(hess + 1e-8 * np.eye(k + 1), grad)
        except np.linalg.LinAlgError:
            delta = np.linalg.lstsq(hess, grad, rcond=None)[0]
        beta = beta + delta
        if np.max(np.abs(delta)) < tol:
            converged = True
            break

    eta = design @ beta
    p = _sigmoid(eta)
    w = np.clip(p * (1 - p), 1e-10, None)
    hess = design.T @ (design * w[:, None])
    try:
        cov = np.linalg.inv(hess)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(hess)

    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(divide='ignore', invalid='ignore'):
        z = np.where(se > 0, beta / se, 0)
    pvals = [p_from_z(zi) for zi in z]

    ll = float(np.sum(yv * np.log(np.clip(p, 1e-12, 1)) +
                      (1 - yv) * np.log(np.clip(1 - p, 1e-12, 1))))
    aic = -2 * ll + 2 * (k + 1)
    bic = -2 * ll + math.log(n) * (k + 1)

    def _safe_exp(value: float) -> float:
        """Prevent exponential overflow due to complete separation. """
        return math.exp(min(700.0, max(-700.0, value)))

    coef = [round(float(b), 4) for b in beta[1:]]
    out = {
        'features': ['(Constant)'] + names,
        'coef': [round(float(beta[0]), 4)] + coef,
        'or': [None] + [round(_safe_exp(b), 3) for b in beta[1:]],
        'ci_low': [None] + [round(_safe_exp(b - 1.96 * s), 3)
                            for b, s in zip(beta[1:], se[1:])],
        'ci_high': [None] + [round(_safe_exp(b + 1.96 * s), 3)
                             for b, s in zip(beta[1:], se[1:])],
        'p': [round(float(pv), 4) for pv in pvals],
        'aic': round(aic, 2), 'bic': round(bic, 2), 'loglik': round(ll, 2),
        'n': int(n), 'events': int(yv.sum()), 'converged': converged,
        # Collinearity / Complete separation diagnosis: If the standard error is too large or the absolute value of the coefficient is too large, the estimation is unstable.
        'unstable': [bool(se[i + 1] > 5 or abs(beta[i + 1]) > 12) for i in range(k)],
        'constant_columns': [names[i] for i in range(k)
                             if float(np.std(arr[:, i])) == 0.0],
    }
    return out


def _normal_cdf(values):
    """Standard Normal Cumulative Distribution Function (Not dependent scipy). """
    arr = np.asarray(values, dtype=float)
    erf = np.frompyfunc(math.erf, 1, 1)
    return 0.5 * (1.0 + erf(arr / math.sqrt(2.0)).astype(float))


def probit_regression(X, y, feature_names=None, max_iter: int = 120,
                      tol: float = 1e-8, l2: float = 0.0,
                      binary=None) -> dict:
    """
    Binary Probit Return (Newton-Raphson / IRLS Maximum likelihood estimation).

    :param X: Independent-variable matrix (n x k)
    :param y: Binary dependent variable (0/1)
    :param feature_names: Independent-variable name
    :param binary: Binary-variable flags used for discrete average marginal effects
    :return: Coefficients, standard errors, z values, p-values, 95% CIs, model-fit statistics, and average marginal effects
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    yv = np.asarray(y, dtype=float)
    n, k = arr.shape
    names = list(feature_names or ['x%d' % (i + 1) for i in range(k)])
    binary_mask = np.asarray(binary if binary is not None else [False] * k,
                             dtype=bool)
    if len(binary_mask) != k:
        binary_mask = np.zeros(k, dtype=bool)

    design = np.column_stack([np.ones(n), arr])
    beta = np.zeros(k + 1)
    converged = False
    penalty = np.eye(k + 1) * l2
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        eta = design @ beta
        mu = np.clip(_normal_cdf(eta), 1e-10, 1 - 1e-10)
        phi = np.clip(np.exp(-0.5 * eta * eta) / math.sqrt(2 * math.pi),
                      1e-12, None)
        weights = phi * phi / np.clip(mu * (1 - mu), 1e-12, None)
        hess = design.T @ (design * weights[:, None]) + penalty
        grad = design.T @ (yv - mu) - penalty @ beta
        try:
            delta = np.linalg.solve(hess + 1e-9 * np.eye(k + 1), grad)
        except np.linalg.LinAlgError:
            delta = np.linalg.lstsq(hess, grad, rcond=None)[0]
        beta = beta + delta
        if np.max(np.abs(delta)) < tol:
            converged = True
            break

    eta = design @ beta
    mu = np.clip(_normal_cdf(eta), 1e-10, 1 - 1e-10)
    phi = np.clip(np.exp(-0.5 * eta * eta) / math.sqrt(2 * math.pi),
                  1e-12, None)
    weights = phi * phi / np.clip(mu * (1 - mu), 1e-12, None)
    hess = design.T @ (design * weights[:, None])
    try:
        cov = np.linalg.inv(hess)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(hess)

    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(divide='ignore', invalid='ignore'):
        z_values = np.where(se > 0, beta / se, 0.0)
    p_values = [p_from_z(float(value)) for value in z_values]

    ll = float(np.sum(yv * np.log(mu) + (1 - yv) * np.log(1 - mu)))
    p_mean = float(np.clip(yv.mean(), 1e-10, 1 - 1e-10))
    ll_null = float(n * (p_mean * math.log(p_mean) +
                         (1 - p_mean) * math.log(1 - p_mean)))
    pseudo_r2 = 1 - ll / ll_null if ll_null else 0.0
    aic = -2 * ll + 2 * (k + 1)
    bic = -2 * ll + math.log(n) * (k + 1)

    def average_marginal_effects(beta_vec):
        """Derivatives are used for continuous variables, For binary categorical variables 0→1 Probability difference calculation AME. """
        eta_vec = design @ beta_vec
        phi_vec = np.clip(
            np.exp(-0.5 * eta_vec * eta_vec) / math.sqrt(2 * math.pi),
            1e-12, None)
        values = []
        for j in range(k):
            if binary_mask[j]:
                x = arr[:, j]
                eta0 = eta_vec - beta_vec[j + 1] * x
                eta1 = eta_vec + beta_vec[j + 1] * (1 - x)
                values.append(float(np.mean(
                    _normal_cdf(eta1) - _normal_cdf(eta0))))
            else:
                values.append(float(beta_vec[j + 1] * np.mean(phi_vec)))
        return np.asarray(values, dtype=float)

    ame = average_marginal_effects(beta)
    gradient = np.zeros((k, k + 1))
    step = 1e-5
    for j in range(k + 1):
        beta_plus = beta.copy()
        beta_minus = beta.copy()
        beta_plus[j] += step
        beta_minus[j] -= step
        gradient[:, j] = (average_marginal_effects(beta_plus) -
                          average_marginal_effects(beta_minus)) / (2 * step)
    ame_var = np.einsum('ij,jk,ik->i', gradient, cov, gradient)
    ame_se = np.sqrt(np.clip(ame_var, 0, None))

    return {
        'features': ['(Constant)'] + names,
        'coef': [round(float(value), 4) for value in beta],
        'se': [round(float(value), 4) for value in se],
        'z': [round(float(value), 4) for value in z_values],
        'p': [round(float(value), 4) for value in p_values],
        'ci_low': [round(float(value - 1.96 * error), 4)
                   for value, error in zip(beta, se)],
        'ci_high': [round(float(value + 1.96 * error), 4)
                    for value, error in zip(beta, se)],
        'ame_features': names,
        'ame': [round(float(value), 4) for value in ame],
        'ame_se': [round(float(value), 4) for value in ame_se],
        'ame_ci_low': [round(float(value - 1.96 * error), 4)
                       for value, error in zip(ame, ame_se)],
        'ame_ci_high': [round(float(value + 1.96 * error), 4)
                        for value, error in zip(ame, ame_se)],
        'aic': round(aic, 2), 'bic': round(bic, 2),
        'loglik': round(ll, 2), 'pseudo_r2': round(pseudo_r2, 4),
        'n': int(n), 'events': int(yv.sum()), 'converged': converged,
        'unstable': [bool(se[i + 1] > 5 or abs(beta[i + 1]) > 12)
                     for i in range(k)],
        'constant_columns': [names[i] for i in range(k)
                             if float(np.std(arr[:, i])) == 0.0],
    }


# ===========================================================================
# Structural Equation Model (Path analysis of observed variables): Fitting index
# ===========================================================================

def _ml_fit(sigma_obs, sigma_imp) -> float:
    """Maximum likelihood fitting function F_ML. """
    p = sigma_obs.shape[0]
    sign_o, logdet_o = np.linalg.slogdet(sigma_obs)
    sign_i, logdet_i = np.linalg.slogdet(sigma_imp)
    if sign_i <= 0 or sign_o <= 0:
        return float('nan')
    try:
        inv_i = np.linalg.inv(sigma_imp)
    except np.linalg.LinAlgError:
        inv_i = np.linalg.pinv(sigma_imp)
    return float(logdet_i - logdet_o + np.trace(sigma_obs @ inv_i) - p)


def sem_fit_indices(sigma_obs, sigma_imp, n: int, n_params: int) -> dict:
    """
    Calculate the fitting index of the structural equation model.

    :param sigma_obs: Observed covariance matrix
    :param sigma_imp: Model-implied covariance matrix
    :param n: Sample size
    :param n_params: Number of free model parameters
    :return: {'chi2','df','chi2_df','cfi','tli','rmsea','srmr',...}
    """
    p = sigma_obs.shape[0]
    f_ml = _ml_fit(sigma_obs, sigma_imp)
    if math.isnan(f_ml) or f_ml < 0:
        f_ml = 0.0
    chi2 = (n - 1) * f_ml
    df = p * (p + 1) / 2 - n_params
    if df <= 0:
        return {'chi2': round(chi2, 2), 'df': int(df), 'chi2_df': None,
                'cfi': None, 'tli': None, 'rmsea': None, 'srmr': None,
                'note': 'The model has insufficient degrees of freedom.'}

    # Baseline (Independent)Model: Only diagonal elements
    sigma_null = np.diag(np.diag(sigma_obs))
    f_null = _ml_fit(sigma_obs, sigma_null)
    chi2_null = (n - 1) * (f_null if not math.isnan(f_null) else 0)
    df_null = p * (p - 1) / 2

    chi2_df = chi2 / df
    cfi = 1 - max(chi2 - df, 0) / max(chi2_null - df_null, 1e-9)
    denom = (chi2_null / df_null) - 1
    tli = ((chi2_null / df_null) - chi2_df) / denom if abs(denom) > 1e-9 else 0.0
    rmsea = math.sqrt(max(chi2 - df, 0) / (df * (n - 1))) if n > 1 else 0.0

    # SRMR: Standardized root mean square of residual
    d_o = np.sqrt(np.diag(sigma_obs))
    d_i = np.sqrt(np.clip(np.diag(sigma_imp), 1e-12, None))
    std_obs = sigma_obs / np.outer(d_o, d_o)
    std_imp = sigma_imp / np.outer(d_i, d_i)
    resid = std_obs - std_imp
    lower = np.tril_indices_from(resid, k=0)
    srmr = math.sqrt(float(np.mean(resid[lower] ** 2)))

    return {
        'chi2': round(chi2, 2), 'df': int(df), 'chi2_df': round(chi2_df, 3),
        'chi2_null': round(chi2_null, 2), 'df_null': int(df_null),
        'cfi': round(cfi, 3), 'tli': round(tli, 3),
        'rmsea': round(rmsea, 3), 'srmr': round(srmr, 3),
        'n': int(n),
        'note': ('Good fit' if cfi >= 0.9 and rmsea <= 0.08 else
                 'The fit is acceptable' if cfi >= 0.8 and rmsea <= 0.1 else 'Poor fit'),
    }


# ===========================================================================
# Survival analysis: Kaplan-Meier with Log-rank Inspection
# ===========================================================================

def kaplan_meier(times, events, label: str = '') -> dict:
    """
    Kaplan-Meier Survival curve.

    :param times: Follow-up duration in days
    :param events: Event indicator (1 = event occurred, 0 = censored)
    :return: {'label','points':[{time,survival,ci_low,ci_high,at_risk,events}], 'median'}
    """
    t = np.asarray(times, dtype=float)
    e = np.asarray(events, dtype=int)
    if len(t) == 0:
        return {'label': label, 'points': [], 'median': None}

    order = np.argsort(t)
    t, e = t[order], e[order]
    uniq = np.unique(t[e == 1])

    survival = 1.0
    cum_var = 0.0
    points = []
    median = None
    for time in uniq:
        at_risk = int(np.sum(t >= time))
        deaths = int(np.sum((t == time) & (e == 1)))
        if at_risk <= 0:
            continue
        survival *= (1 - deaths / at_risk)
        if at_risk - deaths > 0:
            cum_var += deaths / (at_risk * (at_risk - deaths))
        se = survival * math.sqrt(cum_var)
        points.append({
            'time': int(time), 'survival': round(survival, 4),
            'ci_low': round(max(0.0, survival - 1.96 * se), 4),
            'ci_high': round(min(1.0, survival + 1.96 * se), 4),
            'at_risk': at_risk, 'events': deaths,
        })
        if median is None and survival <= 0.5:
            median = int(time)
    return {'label': label, 'points': points, 'median': median,
            'n': int(len(t)), 'events': int(e.sum())}


def logrank_test(times_a, events_a, times_b, events_b) -> dict:
    """
    Two groups Log-rank Inspection.

    :return: {'chi2', 'df', 'p', 'o1', 'e1'}
    """
    ta, ea = np.asarray(times_a, float), np.asarray(events_a, int)
    tb, eb = np.asarray(times_b, float), np.asarray(events_b, int)
    event_times = np.unique(np.concatenate([ta[ea == 1], tb[eb == 1]]))
    if len(event_times) == 0:
        return {'chi2': 0.0, 'df': 1, 'p': 1.0, 'o1': 0, 'e1': 0.0}

    o1 = e1 = v = 0.0
    for time in event_times:
        n1 = float(np.sum(ta >= time))
        n2 = float(np.sum(tb >= time))
        d1 = float(np.sum((ta == time) & (ea == 1)))
        d2 = float(np.sum((tb == time) & (eb == 1)))
        n, d = n1 + n2, d1 + d2
        if n < 2 or d == 0:
            continue
        o1 += d1
        e1 += d * n1 / n
        v += n1 * n2 * d * (n - d) / (n * n * (n - 1))
    chi2 = ((o1 - e1) ** 2 / v) if v > 0 else 0.0
    return {'chi2': round(chi2, 3), 'df': 1, 'p': round(chi2_p_value(chi2, 1), 4),
            'o1': int(o1), 'e1': round(e1, 2)}


# ===========================================================================
# Collinearity diagnosis
# ===========================================================================

def vif(X, names=None) -> list:
    """
    Variance inflation factor (VIF).

    VIF_j = 1 / (1 - R²_j), of which R²_j For the th j Determination coefficient of regression of independent variables to other independent variables.
    Empirical judgment: VIF > 10 Severe collinearity is indicated, > 5 Needs attention.

    :return: [{'name', 'vif', 'r2', 'level'}, ...]
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    names = list(names or ['x%d' % (i + 1) for i in range(arr.shape[1])])
    out = []
    for j in range(arr.shape[1]):
        others = np.delete(arr, j, axis=1)
        if others.shape[1] == 0:
            out.append({'name': names[j], 'vif': 1.0, 'r2': 0.0, 'level': 'Normal'})
            continue
        r2 = standardized_regression(others, arr[:, j])['r2']
        value = 1.0 / (1.0 - r2) if r2 < 1.0 else float('inf')
        level = '"Serious (>10)' if value > 10 else ('Needs attention (>5)' if value > 5 else 'Normal')
        out.append({'name': names[j], 'vif': round(value, 3) if value != float('inf') else 999.0,
                    'r2': round(r2, 4), 'level': level})
    return out


# ===========================================================================
# Multiple comparison correction
# ===========================================================================

def fdr_bh(p_values) -> list:
    """
    Benjamini-Hochberg FDR Adjusted (Control the error detection rate).

    :param p_values: Original p Value sequence
    :return: Corrected p-values (same length as the input sequence)
    """
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * n / np.arange(1, n + 1)
    # Ensure monotonicity: Take cumulative minimum from largest to smallest
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    out = np.empty(n, dtype=float)
    out[order] = adjusted
    return [round(float(v), 4) for v in out]


def bonferroni(p_values) -> list:
    """Bonferroni Adjusted: p × Number of inspections (Upper limit 1). """
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    if n == 0:
        return []
    return [round(min(1.0, float(v) * n), 4) for v in p]


def sig_flag(p, alpha: float = 0.05) -> str:
    """the p Value converted to saliency marker. """
    if p is None:
        return ''
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < alpha:
        return '*'
    return 'ns'


# ===========================================================================
# Model calibration
# ===========================================================================

def brier_score(y_true, y_prob) -> float:
    """Brier Score (Lower is better; 0.25 It is equivalent to an information-free model). """
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_prob, dtype=float)
    return round(float(np.mean((p - y) ** 2)), 4)


def hosmer_lemeshow(y_true, y_prob, groups: int = 10) -> dict:
    """
    Hosmer-Lemeshow Goodness-of-fit test.

    Group by predicted probability decibels, Compare the observation frequency of each group with the expected frequency.
    P > 0.05 indicates that the model is well calibrated and does not reject a well-fitting null hypothesis.
    """
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_prob, dtype=float)
    n = len(y)
    if n < groups * 2 or len(np.unique(y)) < 2:
        return {'chi2': 0.0, 'df': 0, 'p': 1.0, 'note': 'Insufficient sample size'}

    order = np.argsort(p)
    y, p = y[order], p[order]
    idx = np.array_split(np.arange(n), groups)
    chi2 = 0.0
    rows = []
    for group in idx:
        if len(group) == 0:
            continue
        obs1 = float(y[group].sum())
        exp1 = float(p[group].sum())
        obs0 = len(group) - obs1
        exp0 = len(group) - exp1
        if exp1 > 0:
            chi2 += (obs1 - exp1) ** 2 / exp1
        if exp0 > 0:
            chi2 += (obs0 - exp0) ** 2 / exp0
        rows.append({'predicted': round(exp1 / len(group), 4),
                     'observed': round(obs1 / len(group), 4), 'n': len(group)})
    df = max(1, len(rows) - 2)
    return {'chi2': round(chi2, 3), 'df': df, 'p': round(chi2_p_value(chi2, df), 4),
            'groups': rows,
            'note': 'Well calibrated' if chi2_p_value(chi2, df) > 0.05 else 'There is poor calibration.'}


def calibration_curve(y_true, y_prob, bins: int = 10) -> list:
    """
    Calibration curve data: Average of predicted probabilities by sub-bin vs Actual incidence rate.
    """
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_prob, dtype=float)
    if len(y) < bins:
        return []
    order = np.argsort(p)
    y, p = y[order], p[order]
    out = []
    for group in np.array_split(np.arange(len(y)), bins):
        if len(group) == 0:
            continue
        out.append({'predicted': round(float(p[group].mean()), 4),
                    'observed': round(float(y[group].mean()), 4),
                    'n': int(len(group))})
    return out


# ===========================================================================
# Scale Reliability and Validity
# ===========================================================================

def cronbach_alpha(X) -> float:
    """
    Cronbach's α Internal consistency coefficient.

    α = k/(k-1) × (1 - Σσ²_item / σ²_total)

    :param X: Item matrix (n participants x k items)
    :return: Cronbach alpha; values >= 0.70 are generally considered acceptable
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    n, k = arr.shape
    if k < 2 or n < 3:
        return 0.0
    item_var_sum = float(arr.var(axis=0, ddof=1).sum())
    total_var = float(arr.sum(axis=1).var(ddof=1))
    if total_var <= 0:
        return 0.0
    alpha = k / (k - 1) * (1 - item_var_sum / total_var)
    return round(float(np.clip(alpha, -1, 1)), 4)


def alpha_if_deleted(X, item_names=None) -> list:
    """After deleting a certain entry α (Used for item filtering). """
    arr = np.asarray(X, dtype=float)
    names = list(item_names or ['item%d' % (i + 1) for i in range(arr.shape[1])])
    out = []
    for j in range(arr.shape[1]):
        rest = np.delete(arr, j, axis=1)
        out.append({'item': names[j], 'alpha': cronbach_alpha(rest)})
    return out


def kmo(X) -> float:
    """
    KMO (Kaiser-Meyer-Olkin)Sampling appropriateness quantity.

    KMO = Σr² / (Σr² + Σp²), of which r Is the correlation coefficient, p It is a partial correlation coefficient.
    "General KMO > 0.7 Suitable for factor analysis.
    """
    arr = np.asarray(X, dtype=float)
    if arr.shape[1] < 2:
        return 0.0
    R = np.corrcoef(arr, rowvar=False)
    try:
        inv = np.linalg.inv(R)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(R)
    d = np.sqrt(np.clip(np.diag(inv), 1e-12, None))
    P = -inv / np.outer(d, d)
    np.fill_diagonal(P, 0.0)
    R0 = R.copy()
    np.fill_diagonal(R0, 0.0)
    num = float((R0 ** 2).sum())
    den = num + float((P ** 2).sum())
    return round(num / den, 4) if den > 0 else 0.0


def bartlett_test(X) -> dict:
    """
    Bartlett Spherical inspection (Verify that the correlation matrix is a unit matrix).

    χ² = -(n-1-(2p+5)/6) × ln|R|, df = p(p-1)/2
    P < 0.05 Indicates that there is a correlation between variables, Suitable for factor analysis.
    """
    arr = np.asarray(X, dtype=float)
    n, p = arr.shape
    if p < 2 or n < 3:
        return {'chi2': 0.0, 'df': 0, 'p': 1.0}
    R = np.corrcoef(arr, rowvar=False)
    sign, logdet = np.linalg.slogdet(R)
    if sign <= 0:
        return {'chi2': 0.0, 'df': p * (p - 1) // 2, 'p': 1.0}
    chi2 = -((n - 1) - (2 * p + 5) / 6.0) * logdet
    df = p * (p - 1) // 2
    return {'chi2': round(float(chi2), 3), 'df': df,
            'p': round(chi2_p_value(float(chi2), df), 4)}


def _varimax(loadings, max_iter: int = 200, tol: float = 1e-6):
    """Variance maximized orthogonal rotation. """
    p, k = loadings.shape
    if k < 2:
        return loadings
    R = np.eye(k)
    prev = 0.0
    for _ in range(max_iter):
        Lam = loadings @ R
        u, s, vt = np.linalg.svd(
            loadings.T @ (Lam ** 3 - Lam @ np.diag(np.diag(Lam.T @ Lam)) / p))
        R = u @ vt
        cur = float(s.sum())
        if prev != 0 and cur / prev < 1 + tol:
            break
        prev = cur
    return loadings @ R


def efa_varimax(X, n_factors: int = 0) -> dict:
    """
    Exploratory factor analysis (Principal component extraction + Variance maximization rotation).

    :param X: Item matrix (n × k)
    :param n_factors: Number of factors; if 0, determine automatically using eigenvalues > 1 (Kaiser criterion)
    :return: {'n_factors','eigenvalues','variance_explained','loadings','communalities'}
    """
    arr = np.asarray(X, dtype=float)
    n, k = arr.shape
    if k < 2 or n < 3:
        return {'n_factors': 0, 'loadings': [], 'note': 'Insufficient number of items'}
    z = (arr - arr.mean(axis=0)) / np.where(arr.std(axis=0, ddof=1) == 0, 1,
                                            arr.std(axis=0, ddof=1))
    R = np.corrcoef(z, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(R)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    if n_factors <= 0:
        n_factors = int((eigvals > 1).sum()) or 1
    n_factors = min(n_factors, k)
    loadings = eigvecs[:, :n_factors] * np.sqrt(np.clip(eigvals[:n_factors], 0, None))
    rotated = _varimax(loadings)
    communalities = (rotated ** 2).sum(axis=1)
    total_var = float(eigvals.sum()) or 1.0
    return {
        'n_factors': int(n_factors),
        'eigenvalues': [round(float(v), 3) for v in eigvals],
        'variance_explained': [round(float(v / total_var * 100), 2)
                               for v in eigvals[:n_factors]],
        'cumulative_variance': round(float(eigvals[:n_factors].sum() / total_var * 100), 2),
        'loadings': [[round(float(v), 3) for v in row] for row in rotated],
        'communalities': [round(float(v), 3) for v in communalities],
    }


def composite_reliability_ave(loadings) -> dict:
    """
    Composite reliability (CR)Compared with the average variance extraction (AVE).

    CR = (Σλ)² / ((Σλ)² + Σ(1-λ²)), AVE = Σλ² / k
    CR ≥ 0.7, AVE ≥ 0.5 It indicates good convergence validity.
    """
    lam = np.asarray(loadings, dtype=float)
    lam = np.abs(lam)
    if lam.size == 0:
        return {'cr': 0.0, 'ave': 0.0}
    sum_lam = float(lam.sum())
    err = float((1 - lam ** 2).sum())
    cr = (sum_lam ** 2) / (sum_lam ** 2 + err) if (sum_lam ** 2 + err) > 0 else 0.0
    ave = float((lam ** 2).mean())
    return {'cr': round(cr, 4), 'ave': round(ave, 4)}


# ===========================================================================
# Mediation effect: Bootstrap Confidence interval
# ===========================================================================

def _ols_coef(X, y):
    """Ordinary least squares, Back (Intercept, Coefficient vector). """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    design = np.column_stack([np.ones(len(arr)), arr])
    beta, *_ = np.linalg.lstsq(design, np.asarray(y, dtype=float), rcond=None)
    return float(beta[0]), beta[1:]


def bootstrap_mediation(x, m, y, n_boot: int = 2000, seed: int = 42,
                        y_binary: bool = False, confidence: float = 0.95) -> dict:
    """
    Mediation effect Bootstrap Inspection.

    Model:
        M = i₁ + a·X + e₁                 (a Path)
        Y = i₂ + c'·X + b·M + e₂          (b Paths and direct effects c')

    Indirect effect = a × b. Use percentiles Bootstrap Method to estimate it 95% Confidence interval,
    If the confidence interval excludes 0, the mediation effect is considered significant; the proportion mediated is also reported..

    :param x: Independent variable ("Exposure)
    :param m: Mediating variable (screening intention in this project)
    :param y: Dependent variable (screening behavior)
    :param n_boot: Number of bootstrap samples
    :param y_binary: Whether the dependent variable is binary (if True, use logistic regression for the b path)
    :return: {'a','b','c_prime','indirect','ci_low','ci_high','p','proportion','n'}
    """
    x = np.asarray(x, dtype=float)
    m = np.asarray(m, dtype=float)
    y = np.asarray(y, dtype=float)

    def _paths(xx, mm, yy):
        _, a = _ols_coef(xx, mm)                       # a Path
        if y_binary:
            mm_std = mm
            model = logistic_regression(np.column_stack([xx, mm_std]), yy,
                                        ['x', 'm'], l2=0.5)
            c_prime = float(model['coef'][1])
            b = float(model['coef'][2])
        else:
            _, coef = _ols_coef(np.column_stack([xx, mm]), yy)
            c_prime, b = float(coef[0]), float(coef[1])
        return float(a[0]), b, c_prime

    a_hat, b_hat, c_hat = _paths(x, m, y)
    indirect = a_hat * b_hat

    rng = np.random.default_rng(seed)
    n = len(y)
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        try:
            aa, bb, _cc = _paths(x[idx], m[idx], y[idx])
            samples.append(aa * bb)
        except Exception:
            continue
    samples = np.asarray(samples, dtype=float)
    if samples.size == 0:
        return {'a': a_hat, 'b': b_hat, 'c_prime': c_hat, 'indirect': indirect,
                'ci_low': None, 'ci_high': None, 'p': None, 'proportion': None, 'n': n}

    alpha = (1 - confidence) / 2
    lo, hi = np.percentile(samples, [alpha * 100, (1 - alpha) * 100])
    # Bootstrap Double tails p value (Proportional by symbol)
    p_value = 2 * min((samples <= 0).mean(), (samples >= 0).mean())
    total = indirect + c_hat
    return {
        'a': round(a_hat, 4), 'b': round(b_hat, 4), 'c_prime': round(c_hat, 4),
        'indirect': round(indirect, 4),
        'ci_low': round(float(lo), 4), 'ci_high': round(float(hi), 4),
        'p': round(float(min(1.0, p_value)), 4),
        'proportion': round(indirect / total * 100, 2) if abs(total) > 1e-9 else None,
        'n': n, 'n_boot': int(samples.size), 'confidence': confidence,
        'significant': bool(lo > 0 or hi < 0),
        'type': ('Some intermediaries' if (lo > 0 or hi < 0) and abs(c_hat) > 1e-9 else
                 ('Complete intermediary' if (lo > 0 or hi < 0) else 'Mediating is not significant.')),
    }


# ===========================================================================
# Interaction test (Likelihood ratio test)
# ===========================================================================

def interaction_test(X_base, X_inter, y, names_base=None, names_inter=None,
                     l2: float = 0.5) -> dict:
    """
    Interaction likelihood ratio test.

    "Compare the -2 log-likelihood of the main-effects model with the model including interaction terms.
    LR = 2(LL_full - LL_reduced) Under the null hypothesis, the likelihood-ratio statistic follows a chi-square distribution with degrees of freedom equal to the number of interaction terms.

    :return: {'lr','df','p','interaction_terms':[...]}
    """
    yv = np.asarray(y, dtype=float)
    n_obs = len(yv)

    def _as_2d(mat):
        """Normalize input to shape (n_obs, k), supporting one-dimensional arrays, transposed arrays, and lists. """
        arr = np.asarray(mat, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        if arr.shape[0] != n_obs and arr.shape[1] == n_obs:
            arr = arr.T
        return arr

    Xb = _as_2d(X_base)
    Xi = _as_2d(X_inter)
    nb = list(names_base or ['b%d' % i for i in range(Xb.shape[1])])
    ni = list(names_inter or ['i%d' % i for i in range(Xi.shape[1])])

    m0 = logistic_regression(Xb, yv, nb, l2=l2)
    m1 = logistic_regression(np.column_stack([Xb, Xi]), yv, nb + ni, l2=l2)
    lr = 2 * (m1['loglik'] - m0['loglik'])
    df = Xi.shape[1]
    p_value = chi2_p_value(max(0.0, lr), df)
    terms = [{'term': n, 'or': m1['or'][len(nb) + 1 + i],
              'ci_low': m1['ci_low'][len(nb) + 1 + i],
              'ci_high': m1['ci_high'][len(nb) + 1 + i],
              'p': m1['p'][len(nb) + 1 + i]}
             for i, n in enumerate(ni)]
    return {'lr': round(float(lr), 3), 'df': int(df), 'p': round(p_value, 4),
            'significant': p_value < 0.05, 'interaction_terms': terms,
            'loglik_reduced': m0['loglik'], 'loglik_full': m1['loglik']}


# ===========================================================================
# Dosage-Reaction trend test (Cochran-Armitage)
# ===========================================================================

def cochran_armitage_trend(success, total, scores=None) -> dict:
    """
    Rate Trend Test for Ordered Grouping (Cochran-Armitage).

    :param success: Number of positive cases in each group
    :param total: Total sample size in each group
    :param scores: Scores of each group (Default: 0, 1, 2, ...)
    :return: {'z','chi2','p','direction'}
    """
    s = np.asarray(success, dtype=float)
    t = np.asarray(total, dtype=float)
    n = float(t.sum())
    if n <= 0:
        return {'z': 0.0, 'chi2': 0.0, 'p': 1.0, 'direction': '-'}
    if scores is None:
        scores = np.arange(len(t), dtype=float)
    scores = np.asarray(scores, dtype=float)
    p_bar = float(s.sum()) / n
    num = float((scores * (s - t * p_bar)).sum())
    var = p_bar * (1 - p_bar) * (float((t * scores ** 2).sum()) -
                                 float((t * scores).sum()) ** 2 / n)
    if var <= 0:
        return {'z': 0.0, 'chi2': 0.0, 'p': 1.0, 'direction': '-'}
    z = num / math.sqrt(var)
    chi2 = z ** 2
    return {'z': round(float(z), 4), 'chi2': round(float(chi2), 3),
            'p': round(chi2_p_value(float(chi2), 1), 4),
            'direction': 'It rises with the increase of the group' if z > 0 else 'It decreased as the group group increased'}


# ===========================================================================
# E-value (Hybrid sensitivity analysis not measured)
# ===========================================================================

def evalue_from_rr(rr: float) -> float:
    """Calculated based on the relative risk E-value. """
    if rr is None or rr <= 0:
        return 0.0
    r = rr if rr >= 1 else 1.0 / rr
    return round(r + math.sqrt(r * (r - 1)), 3)


def evalue_from_or(or_value: float, ci_low: float = None) -> dict:
    """
    Estimated by the odds ratio E-value ("Adopt RR ≈ √OR Common approximations).

    E-value "Indicate: To have the observed association completely interpreted by unmeasured confounding,
    The confounding factor must be at least as strong as the exposure and outcome (RR Scale).
    """
    if not or_value or or_value <= 0:
        return {'evalue': 0.0, 'evalue_ci': 0.0}
    rr = math.sqrt(or_value)
    out = {'evalue': evalue_from_rr(rr), 'rr_approx': round(rr, 3)}
    if ci_low and ci_low > 0:
        ci_rr = math.sqrt(ci_low)
        out['evalue_ci'] = evalue_from_rr(ci_rr if ci_rr >= 1 else 1 / ci_rr)
    else:
        out['evalue_ci'] = 0.0
    return out


# ===========================================================================
# Competitive risk: Cumulative incidence function (Aalen-Johansen)
# ===========================================================================

def cumulative_incidence(times, status) -> dict:
    """
    Cumulative incidence of competitive risk (Aalen-Johansen Estimate).

    :param times: Follow-up duration
    :param status: 1=event of interest, 2=competing event, 0=Censoring
    :return: {'points':[{'time','cif','se'}], 'final'}
    """
    t = np.asarray(times, dtype=float)
    s = np.asarray(status, dtype=int)
    if len(t) == 0:
        return {'points': [], 'final': 0.0}
    order = np.argsort(t)
    t, s = t[order], s[order]
    event_times = np.unique(t[s > 0])

    survival = 1.0
    cif = 0.0
    var_sum = 0.0
    points = []
    for time in event_times:
        at_risk = int(np.sum(t >= time))
        d_all = int(np.sum((t == time) & (s > 0)))
        d_main = int(np.sum((t == time) & (s == 1)))
        if at_risk <= 0:
            continue
        if d_main > 0:
            cif += survival * d_main / at_risk
            if at_risk - d_main > 0:
                var_sum += (d_main / at_risk) ** 2 / (at_risk - d_main)
        # Update overall survival (The combination of all events)
        if d_all > 0:
            survival *= (1 - d_all / at_risk)
        points.append({'time': int(time), 'cif': round(cif, 4),
                       'se': round(math.sqrt(var_sum) if var_sum > 0 else 0.0, 4)})
    return {'points': points, 'final': round(cif, 4),
            'n': int(len(t)), 'events': int((s == 1).sum()),
            'competing': int((s == 2).sum())}


# ===========================================================================
# Propensity score
# ===========================================================================

def propensity_scores(X, treatment, l2: float = 0.5):
    """Estimate the propensity score (Exposure probability). """
    arr = np.asarray(X, dtype=float)
    t = np.asarray(treatment, dtype=float)
    mu, sd = arr.mean(axis=0), arr.std(axis=0)
    sd[sd == 0] = 1.0
    model = logistic_regression((arr - mu) / sd, t, l2=l2)
    beta = np.asarray(model['coef'], dtype=float)
    eta = beta[0] + ((arr - mu) / sd) @ beta[1:]
    ps = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
    return np.clip(ps, 0.01, 0.99), model


def smd(x_treat, x_ctrl) -> float:
    """Standardized mean difference (SMD). """
    a = np.asarray(x_treat, dtype=float)
    b = np.asarray(x_ctrl, dtype=float)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    if pooled == 0:
        return 0.0
    return round(abs(a.mean() - b.mean()) / pooled, 4)


def propensity_match(ps, treatment, caliper: float = 0.05) -> list:
    """
    Propensity score 1:1 Nearest neighbor matching (Caliper value limit).

    :return: List of matched index pairs [(treated-group index, control-group index), ...]
    """
    ps = np.asarray(ps, dtype=float)
    t = np.asarray(treatment, dtype=int)
    treated = np.where(t == 1)[0]
    control = np.where(t == 0)[0]
    used = set()
    pairs = []
    for i in sorted(treated, key=lambda k: ps[k]):
        best, best_d = -1, caliper
        for j in control:
            if j in used:
                continue
            d = abs(ps[i] - ps[j])
            if d < best_d:
                best, best_d = j, d
        if best >= 0:
            used.add(best)
            pairs.append((int(i), int(best)))
    return pairs


def iptw_weights(ps, treatment) -> list:
    """Inverse probability weighted weight (IPTW). """
    ps = np.asarray(ps, dtype=float)
    t = np.asarray(treatment, dtype=int)
    w = np.where(t == 1, 1.0 / np.clip(ps, 1e-6, None), 1.0 / np.clip(1 - ps, 1e-6, None))
    return w.tolist()


# ===========================================================================
# Missing values: Report and iterative interpolation
# ===========================================================================

def missing_report(df) -> list:
    """Generate Missing Columns Report. """
    out = []
    total = len(df)
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        out.append({'column': str(col), 'missing': n_missing,
                    'rate': round(n_missing / total * 100, 2) if total else 0.0})
    return sorted(out, key=lambda x: x['missing'], reverse=True)


def mice_impute(df, numeric_columns=None, max_iter: int = 10, seed: int = 42):
    """
    Iterative regression imputation (MICE Simplified implementation, Only handle numerical variables).

    For each column with missing values, fit a linear regression using the remaining columns (complete values and current imputed values).
    Iterate and update until convergence. Compared with direct deletion, It can reduce selection bias.

    :return: (Imputed DataFrame, imputation log)
    """
    rng = np.random.default_rng(seed)
    result = df.copy()
    cols = [c for c in (numeric_columns or result.columns)
            if c in result.columns and result[c].isna().any()]
    if not cols:
        return result, []

    # Initial filling: Median
    for col in cols:
        result[col] = result[col].fillna(result[col].median())

    log = []
    for iteration in range(max_iter):
        changed = 0.0
        for col in cols:
            others = [c for c in result.columns if c != col]
            numeric_others = [c for c in others
                              if np.issubdtype(result[c].dtype, np.number)]
            if not numeric_others:
                continue
            mask = df[col].isna().values
            if mask.sum() == 0:
                continue
            X = result.loc[~mask, numeric_others].values.astype(float)
            y = df.loc[~mask, col].values.astype(float)
            if len(y) < 5:
                continue
            design = np.column_stack([np.ones(len(X)), X])
            beta, *_ = np.linalg.lstsq(design, y, rcond=None)
            Xm = result.loc[mask, numeric_others].values.astype(float)
            pred = np.column_stack([np.ones(len(Xm)), Xm]) @ beta
            noise = rng.normal(0, max(1e-6, float(np.std(y - design @ beta))), len(pred))
            new_values = pred + noise
            changed += float(np.abs(new_values - result.loc[mask, col].values).mean())
            result.loc[mask, col] = new_values
        log.append({'iteration': iteration + 1, 'mean_change': round(changed, 6)})
        if changed < 1e-6:
            break
    return result, log


# ===========================================================================
# Discriminative ability: AUC
# ===========================================================================

def auc(y_true, y_score) -> float:
    """
    ROC Area under the curve (Based on the rank sum formula, Support parallel values).

    :param y_true: "True label" (0/1)
    :param y_score: Predicted score
    :return: AUC; Return if only one category is included 0.5
    """
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(y_score, dtype=float)
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    if pos == 0 or neg == 0:
        return 0.5
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    sorted_s = s[order]
    i = 0
    while i < len(sorted_s):
        j = i
        while j + 1 < len(sorted_s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    rank_pos = float(ranks[y == 1].sum())
    return (rank_pos - pos * (pos + 1) / 2.0) / (pos * neg)
