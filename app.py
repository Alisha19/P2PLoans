from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask.ext.mysql import MySQL
from passlib.hash import sha256_crypt
import sys, math

import web3
from web3 import Web3
from solc import compile_source
from web3.contract import ConciseContract

app = Flask(__name__)
mysql = MySQL()

# Blockchain part #

# Run-only-once-in-the-start part begins
src = open('P2PLending.sol')
src = "\n".join(list(line.replace("\n", "") for line in src))
print("Contract Code Loaded")

w3provider = Web3(web3.providers.rpc.HTTPProvider("http://localhost:8545"))
compiled_sol = compile_source(src)
contract_interface = compiled_sol['<stdin>:P2PLending']

P2PLending_contract = w3provider.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
tx_hash = P2PLending_contract.deploy(transaction={'from': w3provider.eth.accounts[0], 'gas': 4100000})
tx_receipt = w3provider.eth.getTransactionReceipt(tx_hash)

contract_address = tx_receipt['contractAddress']
print("Contract is deployed at the address ", contract_address)

contract_read_interface = w3provider.eth.contract(contract_interface['abi'], contract_address,
                                                  ContractFactoryClass=ConciseContract)
contract_txn_interface = P2PLending_contract(contract_address)
# Run-only-once-in-the-start part ends

def create_account(password, name, borrower):
    account_address = w3provider.personal.newAccount(password)

    # Give some ether to fund gas for txns
    w3provider.eth.sendTransaction(
        {'from': w3provider.eth.accounts[0], 'to': account_address, 'gas': 4100000, 'value': 50000000})

    # Unlock for 3 seconds to run the create<User> Txns
    w3provider.personal.unlockAccount(account_address, password, 3)

    if borrower == "True":
        contract_txn_interface.transact({'from': account_address, 'gas': 4100000}).createBorrower(name)
    else:
        contract_txn_interface.transact({'from': account_address, 'gas': 4100000}).createInvestor(name)

    return account_address


def login(account_address, password):
    # TODO: Store address in session variable
    try:
        w3provider.personal.unlockAccount(account_address, password, 3600)
        is_borrower = contract_read_interface.isBorrower(account_address)
        is_investor = contract_read_interface.isInvestor(account_address)
        if is_borrower:
            return [True, "borrower"]
        elif is_investor:
            return  [True, "investor"]
        else:
            return [False, "INVALID"]
    except:
        return [False, None]


def logout(account_address):
    try:
        web3.personal.lockAccount(account_address)
        # TODO: Destroy the session variable that stores the address
        return True
    except:
        return False


def check_balance(account_address):
    # TODO: On login, save account_address to global, maybe?
    return contract_txn_interface.call({'from': account_address, 'gas': 4100000}).viewBalance()


def withdraw(account_address, amount):
    try:
        contract_txn_interface.transact({'from': account_address, 'gas': 4100000}).withdraw(int(amount))
        return True
    except:
        return False


def deposit(account_address, amount):
    contract_txn_interface.transact({'from': account_address, 'gas': 4100000}).deposit(int(amount))
    return True


def squishify(*args, **kwargs):
    name = kwargs['name']
    age = kwargs['age']
    job = kwargs['job']
    gender = kwargs['gender']
    marr_status = kwargs['marr_status']
    liab = kwargs['liab']
    housing = kwargs['housing']
    res_since = kwargs['res_since']
    status_ca = kwargs['status_ca']
    duration = kwargs['duration']
    purpose = kwargs['purpose']
    cred_amt = kwargs['cred_amt']
    sav_act = kwargs['sav_act']
    emp_since = kwargs['emp_since']
    inst_rate = kwargs['inst_rate']
    debtors = kwargs['debtors']
    _property = kwargs['_property']
    plans = kwargs['plans']
    exist_cred = kwargs['exist_cred']
    phone = kwargs['phone']
    foreign = kwargs['foreign']
    return "~".join([name, age, job, gender, marr_status, liab, housing, res_since, status_ca, duration, purpose,
                     cred_amt, sav_act, emp_since, inst_rate, debtors, _property, plans, exist_cred, phone, foreign])


def desquishify(compressed_string):
    s = compressed_string.split('~')
    return {
        'name': s[0],'age': s[1],'job': s[2],
        'gender': s[3],'marr_status': s[4],'liab': s[5],
        'housing': s[6],'res_since': s[7],'status_ca': s[8],
        'duration': s[9],'purpose': s[10],'cred_amt': s[11],
        'sav_act': s[12],'emp_since': s[13],'inst_rate':[14],
        'debtors': s[15], '_property': s[16], 'plans': s[17],
        'exist_cred': s[18], 'phone': s[19], 'foreign': s[20]
    }


def create_application(account_address, duration, interest_rate, credit_amount, otherData):
    try:
        contract_txn_interface.transact({'from': account_address, 'gas': 4100000}) \
            .createApplication(int(duration), int(interest_rate), int(credit_amount), otherData)
        return True
    except:
        return False


def get_num_applications():
    return contract_txn_interface.call({'from': w3provider.eth.accounts[0], 'gas': 4100000}).getNumApplications()


def get_num_loans():
    return contract_txn_interface.call({'from': w3provider.eth.accounts[0], 'gas': 4100000}).getNumLoans()


def view_open_applications():
    open_applications = []
    n = get_num_applications()
    for i in range(1, n + 1):
        is_open = contract_read_interface.ifApplicationOpen(i)
        if is_open:
            raw_data = contract_read_interface.getApplicationData(i)
            other_data = desquishify(raw_data[1])
            open_applications.append({
                'application_id': raw_data[0][0], 
                'duration': raw_data[0][1],		  
                'amount': raw_data[0][2],         
                'interest_rate': raw_data[0][3],  
                'name': other_data['name'],     
                'purpose': other_data['purpose'],
                'job': other_data['job'],
                'age': other_data['age'],
                'category': 2,
                'confidence': 95,
                'borrower': raw_data[2]
            })
    return open_applications


def view_my_application(account_address):
    n = get_num_applications()
    for i in range(1, n + 1):
        is_open = contract_read_interface.ifApplicationOpen(i)
        if is_open:
            raw_data = contract_read_interface.getApplicationData(i)
            if raw_data[2].lower() == account_address.lower():
                return {
                    'application_id': raw_data[0][0],
                    'duration': raw_data[0][1],
                    'amount': raw_data[0][2],
                    'interest_rate': raw_data[0][3],
                    # TODO: De-squishify other_data
                    'other_data': raw_data[1],
                    'borrower': raw_data[2]
                }
    return False


def view_application_by_id(index):
    n = get_num_applications()
    if index > n or index < 1:
        return False
    else:
        raw_data = contract_read_interface.getApplicationData(index)
        return desquishify(raw_data[1])


def view_loan_by_id(index):
    n = get_num_loans()
    if index > n or index < 1:
        return False
    else:
        raw_data = contract_read_interface.getLoanData(index)
        return {
            'loan_id': raw_data[0][0],
            'interest_rate': raw_data[0][1],
            'duration': raw_data[0][2],
            'principal_amount': raw_data[0][3],
            'original_amount': raw_data[0][4],
            'paid_amount': raw_data[0][5],
            'start_time': raw_data[0][6],
            'monthly_checkpoint': raw_data[0][7],
            'application_id': raw_data[0][8],
            'borrower': raw_data[1],
            'investor': raw_data[2]
        }


def grant_loan(account_address, app_id):
    try:
        contract_txn_interface.transact({'from': account_address, 'gas': 41000000}).grantLoan(int(app_id))
        return True
    except:
        return False


def view_my_loan(account_address, userType):
    if userType == "borrower":
        n = get_num_loans()
        for i in range(1, n + 1):
            is_open = contract_read_interface.ifLoanOpen(i)
            if is_open:
                raw_data = contract_read_interface.getLoanData(i)
                if raw_data[1].lower() == account_address.lower():
                    return {
                        'loan_id': raw_data[0][0],
                        'interest_rate': raw_data[0][1],
                        'duration': raw_data[0][2],
                        'principal_amount': raw_data[0][3],
                        'original_amount': raw_data[0][4],
                        'paid_amount': raw_data[0][5],
                        'start_time': raw_data[0][6],
                        'monthly_checkpoint': raw_data[0][7],
                        'application_id': raw_data[0][8],
                        'borrower': raw_data[1],
                        'investor': raw_data[2]
                    }
        return False
    elif userType == "investor":
        n = get_num_loans()
        for i in range(1, n + 1):
            is_open = contract_read_interface.ifLoanOpen(i)
            if is_open:
                raw_data = contract_read_interface.getLoanData(i)
                if raw_data[2].lower() == account_address.lower():
                    return {
                        'loan_id': raw_data[0][0],
                        'interest_rate': raw_data[0][1],
                        'duration': raw_data[0][2],
                        'principal_amount': raw_data[0][3],
                        'original_amount': raw_data[0][4],
                        'paid_amount': raw_data[0][5],
                        'start_time': raw_data[0][6],
                        'monthly_checkpoint': raw_data[0][7],
                        'application_id': raw_data[0][8],
                        'borrower': raw_data[1],
                        'investor': raw_data[2]
                    }
        return False
    else:
        return False


def estimate_interest(account_address, userType):
    if userType == "investor":
        return False
    else:
        pass


# TODO: Remove this test script later
add = create_account("foo", "foo", borrower="True")
print(login(add, "foo"))
print("Login done")
print("Creating application", create_application(add, 10, 1, 100, squishify(name = 'Alisha', age = '21', job = 'wtf', 
								gender = 'f', marr_status = 'blh', liab = 'hh', housing = 'ff', res_since = 'fff', 
								status_ca = 'dd', duration = '222', purpose = 'education', cred_amt = '2255', 
								sav_act = '44444', emp_since = '5', inst_rate = '11', debtors = '2', _property = 'fds', 
								plans = '22', exist_cred = '9', phone = 'yes', foreign = 'no')))

add = create_account("bar", "bar", borrower="True")
print(login(add, "bar"))
print("Login done")
print("Creating application", create_application(add, 10, 1, 100, squishify(name = 'Bhaumik', age = '21', job = 'ftw', 
								gender = 'f', marr_status = 'blh', liab = 'hh', housing = 'ff', res_since = 'fff', 
								status_ca = 'dd', duration = '222', purpose = 'education', cred_amt = '2255', 
								sav_act = '44444', emp_since = '5', inst_rate = '11', debtors = '2', _property = 'fds', 
								plans = '22', exist_cred = '9', phone = 'yes', foreign = 'no')))

# MySQL config
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'p2p_loan'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()

@app.route("/")
def main():
	return render_template('index.html')

@app.route("/signup/", methods = ['GET', 'POST'])
def signup():
	if request.method == 'POST': 
		# Sign Up
		if request.form['btn'] == 'Sign Up':
			name = request.form['su_name']
			password = request.form['su_password']
			borrower = request.form['client_type'] # False for investors, True for borrowers

			account_address = create_account(password, name, borrower)

			return render_template('signup.html', account_address = account_address)

		# Login
		else:
			account_address = request.form['l_acc_add']
			password = request.form['l_password']
			
			success, client_type = login(account_address, password)

			if success:
				session['logged_in'] = True
				session['account_address'] = account_address
				session['client_type'] = client_type
				return (redirect(url_for('inv_dashboard'))) if client_type == 'investor' else (redirect(url_for('appl_dashboard')))
			else:
				return render_template('signup.html', error_l_pass = "Invalid credentials.")

	return render_template('signup.html', account_address = None) 

@app.route("/inv_dashboard/")
def inv_dashboard():
	apps = view_open_applications()
	napps = len(apps)
	to_hide = 0
	if napps % 3 == 1: # get number of blank cards
		to_hide = 2
	elif napps % 3 == 2:
		to_hide = 1
	ndecks = math.ceil(napps/3) # for 3 cards per deck
	return render_template('inv_dashboard.html', apps=apps, ndecks=ndecks, to_hide=to_hide)

@app.route("/view_app/")
def view_app():
	app_id = int(request.args.get('app_id', None))
	app = view_application_by_id(app_id)
	return render_template('view_app.html', app = app, grant_loan = grant_loan, app_id = app_id)

@app.route("/deposit/", methods = ['POST'])
def deposit_amt():
	success = deposit(session['account_address'], request.form['deposit_amt'])
	return render_template('inv_dashboard.html', success = success)

@app.route("/appl_dashboard/", methods = ['GET', 'POST'])
def appl_dashboard():
	cursor.execute('SELECT * FROM open_applications')
	apps = cursor.fetchall()
	napps = len(apps)
	to_hide = 0
	if napps % 3 == 1: # get number of blank cards
		to_hide = 2
	elif napps % 3 == 2:
		to_hide = 1
	ndecks = math.ceil(napps/3) # for 3 cards per deck

	if request.method == 'POST':

		# mapping from 0, 1, 2 to actual value
		jobs = {'1': 'Unemployed/ Unskilled - non-resident', '2': 'Unskilled - resident', '3': 'Skilled employee / Official', '4': 'Management/ Self-employed/ Highly qualified employee/ Officer'}
		genders = {'0': 'Male', '1': 'Female'}
		marr_statuses = {'1': 'Married', '2': 'Single', '3': 'Divorced/ Separated', '4': 'Widowed'}
		housings = {'1': 'Rent', '2': 'Own', '3': 'For free'}
		status_cas = {'1': 'Less than 0', '2': 'Between 0 and 200', '3': 'More than 200', '4': 'No checking account'}
		purposes = {'1': 'Car (new)', '2': 'Car (used)', '3': 'Furniture/ Equipment', '4': 'Radio/ Television', '5': 'Domestic appliances', '6': 'Repairs', '7': 'Education', '8': 'Vacation', '9': 'Retraining', '10': 'Business', '11': 'Others'}
		sav_acts = {'1': 'Less than 100', '2': 'Between 100 and 500', '3': 'Between 500 and 1000', '4': 'More than 1000', '5': 'Unknown/ No savings account'}
		emp_sinces = {'1': 'Unemployed', '2': 'Less than 1 year', '3': 'Between 1 and 4 years', '4': 'Between 4 and 7 years', '5': 'More than 7 years'}
		debtorss = {'1': 'None', '2': 'Co-applicant', '3': 'Guarantor'}
		propertys = {'1': 'Real estate', '2': 'Life Insurance', '3': 'Car or other', '4': 'Unknown/ No property'}
		planss = {'1': 'Bank', '2': 'Stores', '3': 'None'}
		phones = {'1': 'Yes, under my name', '2': 'No'}
		foreigns = {'1': 'Yes', '2': 'No'}

		name = request.form['name']
		age = request.form['age']
		job = jobs[request.form['job']]
		gender = genders[request.form['gender']]
		marr_status = marr_statuses[request.form['marr_status']]
		liab = request.form['liab']
		housing = housings[request.form['housing']]
		res_since = request.form['res_since']
		status_ca = status_cas[request.form['status_ca']]
		duration = request.form['duration']
		purpose = purposes[request.form['purpose']]
		cred_amt = request.form['cred_amt']
		sav_act = sav_acts[request.form['sav_act']]
		emp_since = emp_sinces[request.form['emp_since']]
		inst_rate = request.form['inst_rate']
		debtors = debtorss[request.form['debtors']]
		_property = propertys[request.form['property']]
		plans = planss[request.form['plans']]
		exist_cred = request.form['exist_cred']
		phone = phones[request.form['phone']]
		foreign = foreigns[request.form['foreign']]

		otherData = squishify(name = name, age = age, job = job, gender = gender, marr_status = marr_status, 
						liab = liab, housing = housing, res_since = res_since, status_ca = status_ca, 
						duration = duration, purpose = purpose, cred_amt = cred_amt, 
						sav_act = sav_act, emp_since = emp_since, inst_rate = inst_rate, debtors = debtors, 
						_property = _property, plans = plans, exist_cred = exist_cred, phone = phone, foreign = foreign)

		success = create_application(session['account_address'], int(duration), int(inst_rate), int(cred_amt), otherData)

		if success:
			return render_template('appl_dashboard.html', apps=apps, ndecks=ndecks, to_hide=to_hide)
		return render_template('appl_dashboard.html', apps=apps, ndecks=ndecks, to_hide=to_hide)

	return render_template('appl_dashboard.html', apps=apps, ndecks=ndecks, to_hide=to_hide)


app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == "__main__":
    app.run(debug=True)