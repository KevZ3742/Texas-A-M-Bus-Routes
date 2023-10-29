import traceback
import time
import urllib3
from urllib3.util.ssl_ import create_urllib3_context
import json
import logging
import sys
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ctx = create_urllib3_context()
ctx.load_default_certs()
ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT

#default to 34
route_num = "34"
route_list = ["12", "15", "22", "26", "27", "31", "34", "35", "36", "40", "47", "48"]
#route_list = ["12"]
print(f"Gathering data for route {route_num}")
http = urllib3.PoolManager(ssl_context=ctx, timeout=urllib3.Timeout(connect=2, read=1))

def post(url, cookie_str):
    global http
    #return http.request("POST", url, headers = {"Cookie": cookie_str})
    return http.request("POST", url)

def get(url, cookie_str):
    global http
    #return http.request("GET", url, headers = {"Cookie": cookie_str})
    return http.request("GET", url)

#route_url = "https://transport.tamu.edu/busroutes.web/Routes?r=34"
nego_url = "https://transport.tamu.edu/busroutes.web/mapHub/negotiate?negotiateVersion=1"
#connectionToken
bus_url = "https://transport.tamu.edu/busroutes.web/mapHub?id="
def query(n_url, q_url, q_body):
    # negotiate and get connectionToken first
    r = http.request("POST", n_url)
    #logging.debug(f"N Status Code: {r.status}")
    nego_str = r.data.decode('utf8').replace("'", '"')
    connectionToken = json.loads(nego_str)["connectionToken"]
    #logging.debug(f"connectionToken: {r.status}")

    # build the request url
    q_url = q_url + connectionToken

    # next sent protocol data
    r = http.request("POST", q_url, body='{"protocol": "json", "version": 1}\u001e')
    #logging.debug(f"P Status Code: {r.status}")

    # finally send query
    r = http.request("POST", q_url, body=q_body + '\u001e')
    #logging.debug(f"Q Status Code: {r.status}")

    # then read repeatedly for data
    response_arr = []
    #while True:
    # apparently only 3 queries are needed
    for i in range(3):
        try:
            r = http.request("GET", q_url)
            if r.status > 299:
                break
            #logging.debug(f"G Status Code: {r.status}")
            res_str = r.data.decode('utf8').replace("'", '"')
            if len(res_str) > 0:
                # trim off the last character
                res_str = res_str[:-1]
            if len(res_str) > 5:
                response_arr.append(res_str)
        except urllib3.exceptions.MaxRetryError:
            break
    return response_arr


while True:
    for r in route_list:
        route_num = r
        print(f"Gathering data for route {route_num}")
        response_arr = []
        try:
            response_arr = query(nego_url, bus_url, f'{{"arguments":["{route_num}"],"invocationId":"0","target":"GetBuses","type":1}}')
            for response in response_arr:
                json_obj = json.loads(response)
                print(json.dumps(json_obj, indent=2))
                if "result" not in json_obj or len(json_obj["result"]) == 0:
                    logging.debug("Skipped due to empty result")
                    continue
                if "error" in json_obj:
                    errorf = open(f"error{route_num}.log", "a")
                    errorf.write(time.ctime() + '\n')
                    errorf.write(response + "\n")
                    errorf.write(str(response_arr) + '\n')
                    errorf.close()

                f = open(f"bus{route_num}.csv", "a")
                f.write(f"{int(time.time())}|{json.dumps(json_obj)}\n")
                f.close()
            #if len(response_arr) > 1:
                #raise ValueError
        except Exception as err:
            errorf = open(f"error{route_num}.log", "a")
            errorf.write(time.ctime() + '\n')
            errorf.write(str(response_arr) + '\n')
            traceback.print_exc(file=errorf)
            traceback.print_exc()
            errorf.close()
    time.sleep(5)


