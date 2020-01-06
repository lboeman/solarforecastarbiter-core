import numpy as np
import pandas as pd
import pytest
import itertools
import calendar

from solarforecastarbiter import datamodel
from solarforecastarbiter.metrics import (calculator, deterministic)


DETERMINISTIC_METRICS = list(deterministic._MAP.keys())
NO_NORM = set(DETERMINISTIC_METRICS) - set(deterministic._REQ_NORM)
NO_REF = set(DETERMINISTIC_METRICS) - set(deterministic._REQ_REF_FX)
NO_REF_NO_NORM = set(NO_NORM) - set(deterministic._REQ_REF_FX)
LIST_OF_CATEGORIES = list(datamodel.ALLOWED_CATEGORIES.keys())


@pytest.fixture()
def create_processed_fxobs(create_datetime_index):
    def _create_processed_fxobs(fxobs, fx_values, obs_values):
        return datamodel.ProcessedForecastObservation(
            fxobs.forecast.name,
            fxobs,
            fxobs.forecast.interval_value_type,
            fxobs.forecast.interval_length,
            fxobs.forecast.interval_label,
            valid_point_count=len(fx_values),
            forecast_values=pd.Series(
                fx_values, index=create_datetime_index(len(fx_values))),
            observation_values=pd.Series(
                obs_values, index=create_datetime_index(len(obs_values)))
        )

    return _create_processed_fxobs


@pytest.fixture()
def create_datetime_index():
    def _create_datetime_index(n_periods):
        return pd.date_range(start='20190801', periods=n_periods, freq='1h',
                             tz='MST', name='timestamp')

    return _create_datetime_index


@pytest.fixture(params=['fxobs', 'fxagg'])
def single_forecast_data_obj(
        request, single_forecast_aggregate,
        single_forecast_observation):
    if request.param == 'fxobs':
        return single_forecast_observation
    else:
        return single_forecast_aggregate


@pytest.fixture()
def proc_fx_obs(create_processed_fxobs, many_forecast_observation):
    proc_fx_obs = []

    for fx_obs in many_forecast_observation:
        proc_fx_obs.append(
            create_processed_fxobs(fx_obs,
                                   np.random.randn(10)+10,
                                   np.random.randn(10)+10)
        )
    return proc_fx_obs


@pytest.fixture()
def ref_fx_obs(create_processed_fxobs, many_forecast_observation):
    ref_fx_obs = create_processed_fxobs(many_forecast_observation[0],
                                        np.random.randn(10)+10,
                                        np.random.randn(10)+10)
    return ref_fx_obs


# Suppress RuntimeWarnings b/c in some metrics will divide by zero or
# don't handle single values well
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
@pytest.mark.parametrize('categories,metrics', [
    pytest.param(
        [], [], marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    pytest.param(
        ['date', 'month'], [],
        marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    pytest.param(
        LIST_OF_CATEGORIES, DETERMINISTIC_METRICS,
        marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    pytest.param(
        LIST_OF_CATEGORIES, NO_NORM,
        marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    (LIST_OF_CATEGORIES, NO_REF),
    (LIST_OF_CATEGORIES, NO_REF_NO_NORM)
])
def test_calculate_metrics_no_reference(
        categories, metrics, proc_fx_obs):
    result = calculator.calculate_metrics(proc_fx_obs,
                                          categories, metrics)

    assert isinstance(result, list)
    assert isinstance(result[0], datamodel.MetricResult)
    assert len(result) == len(proc_fx_obs)


@pytest.mark.filterwarnings('ignore::RuntimeWarning')
@pytest.mark.parametrize('categories,metrics', [
    pytest.param(
        [], [], marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    pytest.param(
        ['date', 'month'], [],
        marks=pytest.mark.xfail(strict=True, type=RuntimeError)),
    (LIST_OF_CATEGORIES, DETERMINISTIC_METRICS),
    (LIST_OF_CATEGORIES, NO_REF),
])
def test_calculate_metrics_with_reference(
        categories, metrics, proc_fx_obs, ref_fx_obs):
    result = calculator.calculate_metrics(proc_fx_obs,
                                          categories, metrics,
                                          ref_pair=ref_fx_obs)

    assert isinstance(result, list)
    assert isinstance(result[0], datamodel.MetricResult)
    assert len(result) == len(proc_fx_obs)


@pytest.mark.filterwarnings('ignore::RuntimeWarning')
def test_calculate_metrics_single(single_forecast_data_obj,
                                  create_processed_fxobs, ref_fx_obs):
    inp = [create_processed_fxobs(single_forecast_data_obj,
                                  np.random.randn(10)+10,
                                  np.random.randn(10)+10)]
    result = calculator.calculate_metrics(inp, LIST_OF_CATEGORIES,
                                          DETERMINISTIC_METRICS,
                                          ref_pair=ref_fx_obs)
    assert isinstance(result, list)
    assert isinstance(result[0], datamodel.MetricResult)
    assert len(result) == 1


@pytest.mark.parametrize('categories,metrics', [
    ([], []),
    (LIST_OF_CATEGORIES, DETERMINISTIC_METRICS)
])
def test_calculate_metrics_with_probablistic(categories, metrics,
                                             create_processed_fxobs,
                                             single_observation,
                                             prob_forecasts):
    prfxobs = datamodel.ForecastObservation(prob_forecasts, single_observation)
    proc_prfx_obs = create_processed_fxobs(prfxobs,
                                           np.random.randn(10)+10,
                                           np.random.randn(10)+10)

    # Error - ProbabilisticForecast not yet supported
    with pytest.raises(NotImplementedError):
        calculator.calculate_metrics([proc_prfx_obs],
                                     categories, metrics)


def test_calculate_deterministic_metrics_no_metrics(ref_fx_obs):
    with pytest.raises(RuntimeError):
        calculator.calculate_deterministic_metrics(
            ref_fx_obs, LIST_OF_CATEGORIES, []
        )


def test_calculate_deterministic_metrics_no_reference(ref_fx_obs):
    with pytest.raises(RuntimeError):
        calculator.calculate_deterministic_metrics(
            ref_fx_obs, LIST_OF_CATEGORIES, DETERMINISTIC_METRICS
        )


def test_calculate_deterministic_metrics_no_reference_data(
        create_processed_fxobs, single_forecast_observation):
    pair = create_processed_fxobs(single_forecast_observation,
                                  np.random.randn(10),
                                  np.random.randn(10))
    ref = create_processed_fxobs(single_forecast_observation,
                                 np.random.randn(0),
                                 np.random.randn(0))

    with pytest.raises(RuntimeError):
        calculator.calculate_deterministic_metrics(
            pair, LIST_OF_CATEGORIES, DETERMINISTIC_METRICS,
            ref_fx_obs=ref
        )


@pytest.mark.parametrize('fx_vals,obs_vals', [
    (np.random.randn(0), np.random.randn(0)),
    (np.random.randn(10), np.random.randn(0)),
    (np.random.randn(0), np.random.randn(10)),
])
def test_calculate_deterministic_metrics_missing_values(
        create_processed_fxobs, single_forecast_observation,
        fx_vals, obs_vals):
    pair = create_processed_fxobs(single_forecast_observation,
                                  fx_vals, obs_vals)
    with pytest.raises(RuntimeError):
        calculator.calculate_deterministic_metrics(
            pair, LIST_OF_CATEGORIES, NO_REF
        )


def test_calculate_deterministic_metrics_normalizer(
        create_processed_fxobs, single_forecast_observation):
    pair = create_processed_fxobs(single_forecast_observation,
                                  np.random.randn(10), np.random.randn(10))
    s0 = calculator.calculate_deterministic_metrics(
        pair, ['total'], deterministic._REQ_NORM, normalizer=1.0)
    s1 = calculator.calculate_deterministic_metrics(
        pair, ['total'], deterministic._REQ_NORM, normalizer=1.0)
    s2 = calculator.calculate_deterministic_metrics(
        pair, ['total'], deterministic._REQ_NORM, normalizer=2.0)
    for s in [s0, s1, s2]:
        assert isinstance(s, datamodel.MetricResult)
    assert s0 == s1
    assert s1 != s2


def test_calculate_deterministic_metrics_reference(
        create_processed_fxobs, single_forecast_observation):
    pair = create_processed_fxobs(single_forecast_observation,
                                  np.random.randn(10), np.random.randn(10))
    ref0 = create_processed_fxobs(single_forecast_observation,
                                  np.random.randn(10), np.random.randn(10))
    ref1 = create_processed_fxobs(single_forecast_observation,
                                  np.random.randn(10), np.random.randn(10))
    s0 = calculator.calculate_deterministic_metrics(
        pair, ['total'], deterministic._REQ_REF_FX,
        ref_fx_obs=ref0)
    s1 = calculator.calculate_deterministic_metrics(
        pair, ['total'], deterministic._REQ_REF_FX,
        ref_fx_obs=ref1)
    for s in [s0, s1]:
        assert isinstance(s, datamodel.MetricResult)
    assert s0 != s1


# Suppress RuntimeWarnings b/c in some metrics will divide by zero or
# don't handle single values well
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
@pytest.mark.parametrize('categories', [
    [],
    *list(itertools.combinations(LIST_OF_CATEGORIES, 1)),
    LIST_OF_CATEGORIES[0:1],
    LIST_OF_CATEGORIES[0:2],
    LIST_OF_CATEGORIES
])
@pytest.mark.parametrize('metrics', [
    *list(itertools.combinations(DETERMINISTIC_METRICS, 1)),
    DETERMINISTIC_METRICS[0:1],
    DETERMINISTIC_METRICS[0:2],
    DETERMINISTIC_METRICS
])
def test_calculate_deterministic_metrics(categories, metrics,
                                         single_forecast_data_obj,
                                         single_forecast_observation,
                                         create_processed_fxobs):
    pair = create_processed_fxobs(single_forecast_data_obj,
                                  np.random.randn(10)+10,
                                  np.random.randn(10)+10)
    ref = create_processed_fxobs(single_forecast_observation,
                                 np.random.randn(10)+10,
                                 np.random.randn(10)+10)
    result = calculator.calculate_deterministic_metrics(
        pair, categories, metrics, ref_fx_obs=ref)
    # Check results
    assert isinstance(result, datamodel.MetricResult)
    assert result.forecast_id == pair.original.forecast.forecast_id
    assert result.name == pair.original.forecast.name
    assert len(result.values) % len(metrics) == 0
    cats = {val.category for val in result.values}
    assert cats == set(categories)
    fx_values = pair.forecast_values
    for cat in categories:
        cat_grps = {v.index for v in result.values if v.category == cat}
        assert len(
            {v.metric for v in result.values if v.category == cat}
        ) == len(metrics)

        # has expected groupings
        if cat == 'month':
            grps = fx_values.groupby(
                fx_values.index.month).groups
            grps = [calendar.month_abbr[g] for g in grps]
        elif cat == 'hour':
            grps = fx_values.groupby(
                fx_values.index.hour).groups
        elif cat == 'year':
            grps = fx_values.groupby(
                fx_values.index.year).groups
        elif cat == 'date':
            grps = fx_values.groupby(
                fx_values.index.date).groups
        elif cat == 'weekday':
            grps = fx_values.groupby(
                fx_values.index.weekday).groups
            grps = [calendar.day_abbr[g] for g in grps]
        elif cat == 'total':
            grps = ['0']
        assert {str(g) for g in grps} == cat_grps
    for val in result.values:
        assert (
            np.isnan(val.value) or
            np.issubdtype(val.value, np.number)
        )


@pytest.mark.parametrize('metric,fx,obs,ref_fx,norm,expect', [
    ('mae', [], [], None, None, np.NaN),
    ('mae', [1, 1, 1], [0, 1, -1], None, None, 1.0),
    ('mbe', [1, 1, 1], [0, 1, -1], None, None, 1.0),
    ('rmse', [1, 0, 1], [0, -1, 2], None, None, 1.0),
    ('nrmse', [1, 0, 1], [0, -1, 2], None, None, None),
    ('nrmse', [1, 0, 1], [0, -1, 2], None, 2.0, 100/2),
    ('mape', [2, 3, 1], [4, 2, 2], None, None, 50.0),
    ('s', [1, 0, 1], [0, -1, 2], None, None, None),
    ('s', [1, 0, 1], [0, -1, 2], [2, 1, 0], None, 0.5),
    ('r', [3, 2, 1], [1, 2, 3], None, None, -1.0),
    ('r^2', [3, 2, 1], [1, 2, 3], None, None, -3.0),
    ('crmse', [1, 1, 1], [0, 1, 2], None, None, np.sqrt(2/3))
])
def test_apply_deterministic_metric_func(metric, fx, obs, ref_fx, norm, expect,
                                         create_datetime_index):
    fx_series = pd.Series(fx, index=create_datetime_index(len(fx)))
    obs_series = pd.Series(obs, index=create_datetime_index(len(obs)))
    # Check require reference forecast kwarg
    if metric in ['s']:
        if ref_fx is None:
            with pytest.raises(KeyError):
                # Missing positional argument
                calculator._apply_deterministic_metric_func(
                    metric, fx_series, obs_series)
        else:
            ref_fx_series = pd.Series(ref_fx,
                                      index=create_datetime_index(len(ref_fx)))
            metric_value = calculator._apply_deterministic_metric_func(
                metric, fx_series, obs_series, ref_fx=ref_fx_series)
            np.testing.assert_approx_equal(metric_value, expect)

    # Check requires normalization kwarg
    elif metric in ['nrmse']:
        if norm is None:
            with pytest.raises(KeyError):
                # Missing positional argument
                calculator._apply_deterministic_metric_func(
                    metric, fx_series, obs_series)
        else:
            metric_value = calculator._apply_deterministic_metric_func(
                metric, fx_series, obs_series, normalizer=norm)
            np.testing.assert_approx_equal(metric_value, expect)

    # Does not require kwarg
    else:
        metric_value = calculator._apply_deterministic_metric_func(
            metric, fx_series, obs_series)
        if np.isnan(expect):
            assert np.isnan(metric_value)
        else:
            np.testing.assert_approx_equal(metric_value, expect)


def test_apply_deterministic_bad_metric_func():
    with pytest.raises(KeyError):
        calculator._apply_deterministic_metric_func('BAD METRIC',
                                                    pd.Series(),
                                                    pd.Series())
