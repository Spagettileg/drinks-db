import math, os, random
from flask import flash, Flask, redirect, render_template, request, session, url_for
from flask_pymongo import PyMongo, pymongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)

# secret.key to be REMOVED prior to submission
# Use an env variable instead
app.secret_key = 'qjfg[73hzd<Gid#-h'

app.config["MONGO_DBNAME"] = 'drinksdb'
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'mongodb://localhost')

mongo = PyMongo(app)


@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@app.route("/")
def index():

    ## Get Quotes - can be refactored - and should be!
    # Get all kv pairs
    allQuotes = (mongo.db.quotes.find_one ({},{ "_id": 0, "quote": 1}))
    # Store just the value array as x
    x = allQuotes.get("quote")
    i = random.randrange(0, len(x),2)
    quoteName = x[i]
    quoteText = x[i+1]
    
    
    # Pagination
    drinks_per_page = 9
    current_page = int(request.args.get('current_page', 1))
    total_drinks = mongo.db.drinks.count()
    num_pages = range(1, int(math.ceil(total_drinks / drinks_per_page)) +1)
    drinks = mongo.db.drinks.find().sort('name', pymongo.ASCENDING).skip((current_page - 1) * drinks_per_page).limit(drinks_per_page)
    
    return render_template('index.html',
        drinks = drinks,
        current_page = current_page,
        pages = num_pages,
        categories = mongo.db.categories.find(),
        quoteName = quoteName,
        quoteText = quoteText)
    
    
@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        user_list = mongo.db.users
        print(user_list)
        current_user = user_list.find_one({'userName': request.form['username']})
        print(current_user)
        if current_user:
            if request.form['password'] == current_user['password']:
                session['username'] = request.form['username']
                return redirect(url_for('index'))
            flash("Incorrect username and/or password. Please try again.")
            return render_template('login.html')
        flash("Username {} does not exist.".format(request.form['username']))
    return render_template('login.html')
    
    
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))
    

@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        user_list = mongo.db.users
        check_existing = user_list.find_one({"userName": request.form['username']})
        if not check_existing:
            user_list.insert_one({"userName": request.form['username'], "password": request.form['password']});
            session['username'] = request.form['username']
            return redirect(url_for('index'))
        flash("Sorry, username '{}' has been taken. Please choose another".format(request.form['username']))
        return redirect(url_for('register'))
    return render_template('register.html')

    
@app.route("/account/<account_name>", methods=['GET', 'POST'])
def account(account_name):
    # Check to make sure account being accessed through url matches
    # account stored in session.
    # This stops users accessing any account through the url bar.
    if account_name == session['username']:
        user = mongo.db.users.find_one({"userName": account_name})
        drinks_submitted_by_user = mongo.db.drinks.find({"userName": account_name})
        drinks_favorited_by_user = mongo.db.drinks.find({"favorites": account_name})

        # For all drinks submitted by the user, calculate their total views &
        # how many times they have been favorited
        total_views = 0
        total_favorites = 0
        for drink in drinks_submitted_by_user:
            total_views += drink['views']
            total_favorites += len(drink['favorites'])
        
        # Get drinks which have been most viewed &
        # favorited by others, for current user
        most_viewed = mongo.db.drinks.find_one({
            "userName": account_name}, sort=[("views", -1)])
        most_favorited = mongo.db.drinks.find_one({
            "userName": account_name}, sort=[("favorites", -1)])
        
        # Get totals for drinks submitted and favorited for the user
        total_drinks_by_user = drinks_submitted_by_user.count()
        total_fave_drinks_by_user = drinks_favorited_by_user.count()
        
        # Pagination - User Submitted Drinks
        drinks_per_page = 4
        drinks_page = int(request.args.get('drinks_page', 1))
        num_dr_pages = range(1, int(math.ceil(total_drinks_by_user / drinks_per_page)) +1)
        drinks_submitted_by_user = mongo.db.drinks.find({"userName": account_name}).sort("dateAdded", -1).skip((drinks_page - 1) * drinks_per_page).limit(drinks_per_page)

        # Pagination - Users Favorite Drinks
        favorite_drinks_per_page = 4
        favorites_page = int(request.args.get('favorites_page', 1))
        num_fv_pages = range(1, int(math.ceil(total_fave_drinks_by_user / favorite_drinks_per_page)) +1)
        drinks_favorited_by_user = mongo.db.drinks.find({"favorites": account_name}).sort("dateAdded", -1).skip((favorites_page - 1) * favorite_drinks_per_page).limit(favorite_drinks_per_page)


        return render_template('account.html',
        user=user,
        users_drinks=drinks_submitted_by_user,
        favorited_drinks=drinks_favorited_by_user,
        # User stats
        views=total_views,
        favorites=total_favorites,
        most_viewed=most_viewed,
        most_favorited=most_favorited,
        total_drinks_by_user=total_drinks_by_user,
        total_fave_drinks_by_user=total_fave_drinks_by_user,
        # Pagination
        drinks_page = drinks_page,
        dr_pages = num_dr_pages,
        favorites_page = favorites_page,
        fv_pages = num_fv_pages)
    
    else:
        return redirect(url_for('account', account_name = session['username']))


@app.route("/drink/<drink_id>", methods=['GET', 'POST'])
def drink(drink_id):
    drink = mongo.db.drinks.find_one({"_id": ObjectId(drink_id)})
    
    # Format Date
    date = datetime.strftime(drink.get('dateAdded'), '%d %B %Y')
    
    # Increment view counter
    # DISABLED FOR NOW. CONFIRMED WORKS, ENABLE LATER ON
    # .update() is depreciated - should use update_one() or find_one_and_update()
    # mongo.db.drinks.update({'_id': ObjectId(drink_id)}, {'$inc': {'views': int(1)}})
    # add a redirect url_for to make sure view increase is shown when viewed?
    # or is this adding redirects for sake of it? Could just always add one via the html display
    # to show this amount before its updated for next view?
    
    # Instructions
    instructions = drink['instructions'].split(". ")

    # Comments
    comment_user, comment_text = [], []
    try:
        all_comments = drink['comments']
    except:
        all_comments = []
    if all_comments:
        
        for comment in all_comments:
            user, text = comment.split(':', 1)
            comment_user.append(user)
            comment_text.append(text)
            
    # Posting a comment
    if request.method == 'POST':
        if len(request.form.get('comment')) > 0:
            new_comment=session['username'] + ":" + request.form.get('comment')
            print(new_comment)
            mongo.db.drinks.find_one_and_update({'_id': ObjectId(drink_id)}, {'$push': {'comments': new_comment}})
            flash("Comment posted, thanks {}".format(session['username']))
            return redirect(url_for('drink', drink_id = drink_id))

    # Check if drink is in users favorites list
    try:
        user_favorites = mongo.db.users.find_one({'userName': session['username']})['favorites']
    except:
        user_favorites=[]
    is_favorite = 1 if drink_id in user_favorites else 0


    return render_template('drink.html',
        drink=drink,
        date=date,
        instructions = instructions,
        is_favorite=is_favorite,
        comment_user = comment_user,
        comment_text = comment_text)


@app.route("/toggle_favorite/<drink_id>/<is_favorite>")
def toggle_favorite(drink_id, is_favorite):
    """Add or remove drink from favorites list for user and drink """
    action = '$pull' if is_favorite == "1" else '$push'
    mongo.db.users.find_one_and_update({'userName': session['username']}, {action: {'favorites': drink_id}})
    mongo.db.drinks.find_one_and_update({'_id': ObjectId(drink_id)}, {action: {'favorites': session['username']}})
    
    return redirect(url_for('drink', drink_id=drink_id, _anchor='fv'))


@app.route("/add_drink", methods=['GET', 'POST'])
def add_drink():
    user = session['username']
    all_categories = mongo.db.categories.find()
    all_glass_types = mongo.db.glass.find()
    all_difficulties = mongo.db.difficulty.find()

    
    if request.method == 'POST':
        dict = request.form.to_dict()
        
        dict['userName']=user
        
        # Add date
        act_date = datetime.strptime(
            datetime.utcnow().isoformat(), '%Y-%m-%dT%H:%M:%S.%f')
        dict['dateAdded']=act_date
        
        # Create view counter
        dict['views']=int(0)
        
        # Sort and process ingredientsq
        ingredients = []
        for k,v in list(dict.items()):
            if ('ingredient' in k) or ('measure' in k):
                ingredients.append(v)
                dict.pop(k)
        
        dict['ingredients'] = ingredients
        dict['favorites'] = []
        dict['comments'] = []
        
        #mongo.db.drinks.insert_one(dict) 

        return redirect(url_for('add_drink'))
    
    return render_template('add_drink.html',
        user=user,
        all_categories=all_categories,
        all_glass_types=all_glass_types,
        all_difficulties=all_difficulties)


@app.route("/edit_drink/<drink_id>", methods=['GET', 'POST'])
def edit_drink(drink_id):
    drink = mongo.db.drinks.find_one({"_id": ObjectId(drink_id)})
    date = datetime.strftime(drink.get('dateAdded'), '%d %B %Y')
    
    # user = session['username']
    all_categories = mongo.db.categories.find()
    all_glass_types = mongo.db.glass.find()
    all_difficulties = mongo.db.difficulty.find()
    
    # Such a crappy piece of code deserves and equally crappy explanation - so get to it.
    # Also, can the nums be auto gen?
    class_num = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10]
    class_name = ['One', 'One', 'Two', 'Two', 'Three', 'Three', 'Four', 'Four', 'Five', 'Five', 'Six', 'Six', 'Seven', 'Seven', 'Eight', 'Eight', 'Nine', 'Nine', 'Ten', 'Ten']
    
    if request.method == 'POST':
            dict = request.form.to_dict()
            
            # Get ingredients
            ingredients = []
            for k,v in list(dict.items()):
                if ('ingredient' in k) or ('measure' in k):
                    ingredients.append(v)
                    dict.pop(k)
            dict['ingredients'] = ingredients
            
            mongo.db.drinks.update_one(drink, {"$set": dict}) 
            flash("UPDATE SUCCESSFUL")    
            return redirect(url_for('drink', drink_id = drink_id))
    
    #########
    #
    # Also, same for HTML for add and edit - is it feasible to somehow combine
    # the 2 pages and have it render whats needed based on add or edit?
    #
    #########
    
    
    
    return render_template('edit_drink.html',
        drink=drink,
        date=date,
        all_categories=all_categories,
        all_glass_types=all_glass_types,
        all_difficulties=all_difficulties,
        class_num=class_num,
        class_name=class_name)



@app.route("/search")
def search():

    # Get Categories for filter dropdowns
    all_categories = mongo.db.categories.find()
    all_glass_types = mongo.db.glass.find()
    all_difficulties = mongo.db.difficulty.find()

    
    if request.args:
        # Take the filters selected by the user and convert them
        # to a dict that can be used in the main search query 
        filters = request.args.to_dict()
        filter_dict={}
        list_of_filters=['category_filter', 'glassType_filter', 'difficulty_filter']
        for k,v in filters.items():
            if k in list_of_filters:
                new_k = k.split("_")[0]
                filter_dict[new_k]=v
        
        # Keep track of filter values when navigating
        # between multiple pages of results.
        try:
            category_filter=filters['category_filter']
        except:
            category_filter=[]
        try:
            glassType_filter=filters['glassType_filter']
        except:
            glassType_filter=[]
        try:
            difficulty_filter=filters['difficulty_filter']
        except:
            difficulty_filter=[]
        
        

        find=request.args['find']

        # Pagination - part 1
        results_per_page = 9
        current_page = int(request.args.get('current_page', 1))
        
        # Query drinks db with search string and filters
        search_str = {'$text': {'$search': find }} if find != "" else {'name': {'$regex': ""}}
        results = mongo.db.drinks.find(
            {'$and': [search_str, filter_dict] }, {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'}), ('views', pymongo.DESCENDING), ('name', pymongo.ASCENDING)]
            ).skip((current_page - 1)*results_per_page).limit(results_per_page)
        
        num_results=results.count()
            
        # If no results for search
        if num_results==0:
            return render_template('search.html',
                find=find,
                num_results=num_results,
                # Items for filters
                all_categories=all_categories,
                all_glass_types=all_glass_types,
                all_difficulties=all_difficulties)
        
        # Pagination - part 2
        num_pages = range(1, int(math.ceil(num_results / results_per_page)) + 1)
        
        # Get values for (example) 'showing 1 - 9 of 15 results' in search results
        x=current_page * results_per_page
        first_result_num = x - results_per_page + 1
        last_result_num = x if x < num_results else num_results
        
        # From search results, find max value of 'score' to allow search.html
        # to calculate the results relevance as a % of highest scoring result
        if find != "":
            max_weight = mongo.db.drinks.find_one({'$and': [{'$text': {'$search': find }}, filter_dict] },{
                'score': {'$meta': 'textScore'}}, sort=[('score', {'$meta': 'textScore'})])['score']
        else:
            max_weight=None
            

        return render_template('search.html',
            find=find,
            # Results 
            results=results,
            first_result_num=first_result_num,
            last_result_num=last_result_num,
            # Search result scores
            max_weight = max_weight,
            # Pagination | Navigation
            results_per_page=results_per_page,
            current_page = current_page,
            pages = num_pages,
            # Pagination | Selected filters
            category_filter=category_filter,
            glassType_filter=glassType_filter,
            difficulty_filter=difficulty_filter,
            # Items for filters
            all_categories=all_categories,
            all_glass_types=all_glass_types,
            all_difficulties=all_difficulties)
    
    return render_template('search.html',
        # Items for filters
        all_categories=all_categories,
        all_glass_types=all_glass_types,
        all_difficulties=all_difficulties)


@app.route("/category/<category_name>", methods=['GET', 'POST'])
def category(category_name):
    category = mongo.db.categories.find_one({"category": category_name})
    drinks = mongo.db.drinks.find({"category": category_name})
    return render_template('category.html',
        category=category,
        drinks = drinks)


## TESTING STUFF

## END TESTING


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
        port=int(os.environ.get('PORT')),
        debug=True)