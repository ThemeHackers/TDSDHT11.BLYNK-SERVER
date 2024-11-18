# modules
# statistics.py
import numpy as np
from scipy.stats import skew, kurtosis

class StatisticalValues:
    @staticmethod
    def mean(data):
        """คำนวณค่าเฉลี่ย"""
        return np.mean(data) if data else None

    @staticmethod
    def standard_deviation(data):
        """คำนวณส่วนเบี่ยงเบนมาตรฐาน"""
        return np.std(data) if data else None

    @staticmethod
    def median(data):
        """คำนวณค่ามัธยฐาน"""
        return np.median(data) if data else None

    @staticmethod
    def max(data):
        """หาค่าสูงสุด"""
        return np.max(data) if data else None

    @staticmethod
    def min(data):
        """หาค่าต่ำสุด"""
        return np.min(data) if data else None

    @staticmethod
    def skewness(data):
        """หาค่าความเอียงของการแจกแจง"""
        return skew(data) if len(data) > 3 else None

    @staticmethod
    def kurtosis(data):
        """หาค่าความโค้งของการแจกแจง"""
        return kurtosis(data) if len(data) > 3 else None

    @staticmethod
    def coefficient_of_variation(data):
        """คำนวณสัมประสิทธิ์ความแปรปรวน"""
        mean = np.mean(data)
        std_dev = np.std(data)
        return (std_dev / mean) * 100 if mean != 0 else None

    @staticmethod
    def percentile(data, percentile_value):
        """คำนวณเปอร์เซ็นไทล์"""
        return np.percentile(data, percentile_value) if data else None

    @staticmethod
    def range(data):
        """คำนวณช่วงของข้อมูล (ค่าสูงสุด - ค่าต่ำสุด)"""
        if data:
            return np.max(data) - np.min(data)
        return None

    @staticmethod
    def variance(data):
        """คำนวณค่าความแปรปรวน (variance)"""
        return np.var(data) if data else None

    @staticmethod
    def interquartile_range(data):
        """คำนวณระยะห่างระหว่างควอไทล์ (IQR)"""
        if data:
            return np.percentile(data, 75) - np.percentile(data, 25)
        return None


