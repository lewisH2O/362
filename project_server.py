from flask import Flask, jsonify, request
import threading,sys,socket,hashlib,json
app = Flask(__name__)

# A list of dicts, e.g. { "id": 12, "desc": "pineappleapplepen", "price": 0, "quantity": 0 }
products = []
lock = threading.Lock()

#This function obtain a time string using the TCP daytime service from HOST
#After that, it convert the string to hex digits
HOST = "time-a-g.nist.gov"
PORT = 13
host = sys.argv[1] if len(sys.argv)>1 else HOST
port = int(sys.argv[2]) if len(sys.argv)>2 else PORT
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    data = s.recv(1024)
    data =  data.decode('utf-8').strip()
    #convert to hex digits form
    exe_id = hashlib.sha256(data.encode()).hexdigest()

#the name of the JSON file
filename = "products.json"
#It is the loading function to get or refresh the products list from the JSON file
def load_products():
    global products
    try:
        with open(filename)as file:
            products = json.load(file)
    except FileNotFoundError:
        products = []
#It is the saving function to store the current products list to the JSON file
def save_product():
    with open(filename, "w") as file:
        json.dump(products, file, indent=2)

#It is the query function, which get the specific product id and return the information of the product
@app.route("/api/products/query/<int:id>", methods=["GET"])
def query_product(id):
    if id is None:
        return jsonify({"status": "error", "reason": "missing product id","exe_id": exe_id}),400
    #refresh the products list
    load_products()
    for item in products["products"]:
        if item["id"] == id:
            return jsonify({"id": item["id"], "desc": item["desc"], "price": item["price"], "quantity": item["quantity"], "exe_id": exe_id})
    #if the specific id is not in the products list, it will return error message
    return jsonify({"status": "error", "reason": "id not found", "exe_id": exe_id}), 404

#It is the buy function, which get the specific product id and receive quantity and card number in json format
@app.route("/api/products/buy/<int:id>", methods=["PUT"])
def buy_product(id):
    data = json.loads(request.data)
    quantity = data.get("quantity")
    card = data.get("card")
    #check if the received information includes id, quantity, and card number and fulfills the standard format
    if id is None:
        return jsonify({"status": "error", "reason": "missing product id","exe_id": exe_id}),400
    if type(id)!=int or id < 0:
        return jsonify({"status": "error", "reason": "product id must be zero or a positive integer","exe_id": exe_id}),400
    if quantity is None:
        return jsonify({"status": "error", "reason": "missing quantity","exe_id": exe_id}),400
    if type(quantity)!=int or quantity<0:
        return jsonify({"status": "error", "reason": "invalid quantity", "exe_id": exe_id}), 400
    if card is None:
        return jsonify({"status": "error", "reason": "missing card number","exe_id": exe_id}),400
    if len(card.strip()) != 16:
        return jsonify({"status": "error", "reason": "card number needs 16 digits", "exe_id": exe_id}),400    
    try:
        int(card)
    except:
        return jsonify({"status": "error", "reason": "card number should be 16 digits", "exe_id": exe_id}),400
    #set a lock for mutual exclusion
    with lock:
        #refresh the products list
        load_products()
        for item in products["products"]:
            #check if the specific id exist in products list
            if item["id"] == id:
                if item["quantity"] >= quantity:
                    item["quantity"] -= quantity
                    #save the products list after changing
                    save_product()
                    amount = int(item["price"])*quantity
                    return jsonify({"status": "success", "amount": amount, "quantity_left": item["quantity"], "exe_id": exe_id})
                #return error message if the required quantity is more than in stock 
                else:
                    return jsonify({"status": "failure", "reason": "insufficient stock", "quantity": item["quantity"], "exe_id": exe_id}),400
        #return error message for not finding the specific id
        return jsonify({"status": "error", "reason": "product id does not exist","exe_id": exe_id}),404

#It is the replenish function, which get the specific product id and receive quantity in json format
@app.route("/api/products/replenish/<int:id>", methods=["PUT"])
def replenish_product(id):
    data = json.loads(request.data)
    quantity = data.get("quantity")
    #check if the received information includes id, and quantity and fulfills the standard format
    if id is None:
        return jsonify({"status": "error", "reason": "missing product id","exe_id": exe_id}),400
    if type(id)!=int or id < 0:
        return jsonify({"status": "error", "reason": "product id must be zero or a positive integer","exe_id": exe_id}),400
    if quantity is None:
        return jsonify({"status": "error", "reason": "missing quantity","exe_id": exe_id}),400
    if type(quantity)!=int or quantity<0:
        return jsonify({"status": "error", "reason": "invalid quantity", "exe_id": exe_id}), 400
    #set a lock for mutual exclusion
    with lock:
        #refresh the products list
        load_products()
        for item in products["products"]:
            #check if the specific id exist in products list
            if item["id"] == id:
                item["quantity"] += quantity
                save_product()
                return jsonify({"status": "success", "new_quantity": item["quantity"], "exe_id": exe_id})
        return jsonify({"status": "error", "reason": "product id does not exist","exe_id": exe_id}),404


if __name__ == "__main__":
    app.run()
