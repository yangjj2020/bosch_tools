import logging

from app.bo.MSTReqPOJO import ReqPOJO
from app.services.report.mst_test.analyzer.brake_plausibility_check_parser import brake_plausibility_check
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main_brake_plausibility_check(req_data: ReqPOJO) -> str:
    output_path = brake_plausibility_check(req_data, brkStMn=True, brkStRed=False, tplt_type='main_brake_plausibility_check')
    return output_path
