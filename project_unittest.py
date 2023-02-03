import json, subprocess, time, unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SERVER = "localhost:5000"

#set up a function to connect to the server
def project_client(url, method="GET", data=None):
    if data:
        data = json.dumps(data).encode("utf-8")
    headers = {"Content-type": "application/json; charset=UTF-8"} \
    if data else {}
    req = Request(url=url, data=data, headers=headers, method=method)
    with urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result

#create a buy function for the use of thread outside of the test class
def buy(id, quantity):
    data = {"quantity": quantity, "card":"1234567812345678"}
    buy_resp = project_client(f"http://{SERVER}/api/products/buy/{id}", "PUT", data)

class TestProductServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_proc = subprocess.Popen(
            ["python", "project_server.py"])
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server_proc.terminate()

    #It would send an id to server and get id, decscription, price, quantity and exe_id response
    def test_query(self):
        query_resp = project_client(f"http://{SERVER}/api/products/query/3")
        self.assertEqual(3,query_resp["id"])
        self.assertEqual("pen",query_resp["desc"])
        self.assertEqual(3,query_resp["price"])
        self.assertEqual(3,query_resp["quantity"])

    #It would query the quantity of the specific product, then send the buy request and compare the quantity left and the previous quantity to check if it minus the exact number
    def test_buy(self):
        test_id = 4
        test_num = 1
        #query product and get the quantity
        query_resp = project_client(f"http://{SERVER}/api/products/query/{test_id}")
        quantity_before_buy = query_resp["quantity"]
        data = {"quantity":test_num, "card":"1234567812345678"}
        buy_resp = project_client(f"http://{SERVER}/api/products/buy/{test_id}", "PUT", data)
        self.assertEqual(quantity_before_buy-test_num,buy_resp["quantity_left"])

    #It would query the specific product to get the current quantity, then plus one to be an invalid quantity
    def test_buy_insufficient_quantity(self):
        test_id = 9
        try:
            #query product and have an invalid quantity
            query_resp = project_client(f"http://{SERVER}/api/products/query/{test_id}")
            invalid_quantity = query_resp["quantity"] + 1
            data = {"quantity": invalid_quantity, "card" : "1234567812345678"}
            buy_resp = project_client(f"http://{SERVER}/api/products/buy/{test_id}", "PUT", data)
            self.assertTrue(False)
        except HTTPError as e:
            self.assertEqual(400, e.code)
    
    #It would query the specific product to get the current quantity, then plus one to be an invalid quantity
    def test_replenish(self):
        test_id = 4
        test_num = 1
        #query product and get the quantity before replenish
        query_resp = project_client(f"http://{SERVER}/api/products/query/{test_id}")
        quantity_before_replenish = query_resp["quantity"]
        data = {"quantity": test_num}
        replenish_resp = project_client(f"http://{SERVER}/api/products/replenish/{test_id}","PUT",data)
        self.assertEqual(quantity_before_replenish+test_num, replenish_resp["new_quantity"])          

    #It would query a product id, which does not exist
    def test_invalid_id(self):
        try:
            query_resp = project_client(f"http://{SERVER}/api/products/query/999")
            self.assertTrue(False)
        except HTTPError as e:
            self.assertEqual(404, e.code)

    #It would send buy and replenish request with invalid data
    def test_invalid_input(self):
        try:
            data = {"quantity": 1, "card":"HKCERTCTF2022WFC"}
            buy_resp = project_client(f"http://{SERVER}/api/products/buy/1", "PUT", data)
            data = {"quantity": -1}
            replenish_resp = project_client(f"http://{SERVER}/api/products/replenish/1","PUT",data)
            self.assertTrue(False)
        except HTTPError as e:
            self.assertEqual(400, e.code)

    
#this function is used for testing mutual exclusivity
    def test_concurrency(self):
        test_id = 7
        query_resp = project_client(f"http://{SERVER}/api/products/query/{test_id}")
        #get the current quantity of the product and set half of it plus one as the testing quantity
        quantity_before = query_resp["quantity"]
        test_quantity = query_resp["quantity"]//2+1
        try:
            with ThreadPoolExecutor() as pool:
                pool.submit(buy,test_id,test_quantity)
                pool.submit(buy,test_id,test_quantity)
            query_resp = project_client(f"http://{SERVER}/api/products/query/{test_id}")
            #compare with the new quantity, it should be previous one minus the quantity of one thread 
            self.assertEqual(quantity_before-test_quantity,query_resp["quantity"])
        except HTTPError as e:
            self.assertEqual(400, e.code)

if __name__ == "__main__":
    unittest.main()
