from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm, LoginForm, PropertyForm
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

# In-memory data store for users and properties
users = []
properties = []
property_id_counter = 1  # Counter to assign unique IDs to properties


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method="sha256")
        user_data = {
            "first_name": form.first_name.data,
            "last_name": form.last_name.data,
            "email": form.email.data,
            "phone_number": form.phone_number.data,
            "password": hashed_password,
            "role": form.role.data,
        }
        users.append(user_data)
        flash("You have successfully registered!", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = next((u for u in users if u["email"] == form.email.data), None)
        if user and check_password_hash(user["password"], form.password.data):
            session["user_id"] = user["email"]
            session["role"] = user["role"]
            flash("Login successful!", "success")
            if user["role"] == "buyer":
                return redirect(url_for("buyer_dashboard"))
            elif user["role"] == "seller":
                return redirect(url_for("seller_dashboard"))
        else:
            flash("Login Unsuccessful. Please check email and password", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/buyer_dashboard", methods=["GET", "POST"])
def buyer_dashboard():
    if "user_id" not in session or session.get("role") != "buyer":
        flash("You must be logged in as a buyer to view this page", "danger")
        return redirect(url_for("login"))

    # Dummy data for testing purposes
    dummy_properties = [
        {
            "id": 1,
            "place": "Downtown",
            "area": 1200,
            "bedrooms": 3,
            "bathrooms": 2,
            "hospitals": 2,
            "colleges": 3,
            "image": "property1.jpg",
            "seller_id": "seller1@example.com",
        },
        {
            "id": 2,
            "place": "Uptown",
            "area": 900,
            "bedrooms": 2,
            "bathrooms": 1,
            "hospitals": 1,
            "colleges": 1,
            "image": "property2.jpg",
            "seller_id": "seller2@example.com",
        },
        {
            "id": 3,
            "place": "Suburb",
            "area": 1500,
            "bedrooms": 4,
            "bathrooms": 2,
            "hospitals": 3,
            "colleges": 2,
            "image": "property3.jpg",
            "seller_id": "seller3@example.com",
        },
    ]

    filtered_properties = dummy_properties + properties

    if request.method == "POST":
        place = request.form.get("place")
        area_min = request.form.get("area_min")
        area_max = request.form.get("area_max")
        bedrooms = request.form.get("bedrooms")
        bathrooms = request.form.get("bathrooms")

        if place:
            filtered_properties = [
                p for p in filtered_properties if place.lower() in p["place"].lower()
            ]
        if area_min:
            filtered_properties = [
                p for p in filtered_properties if p["area"] >= int(area_min)
            ]
        if area_max:
            filtered_properties = [
                p for p in filtered_properties if p["area"] <= int(area_max)
            ]
        if bedrooms:
            filtered_properties = [
                p for p in filtered_properties if p["bedrooms"] == int(bedrooms)
            ]
        if bathrooms:
            filtered_properties = [
                p for p in filtered_properties if p["bathrooms"] == int(bathrooms)
            ]

    return render_template("buyer_dashboard.html", properties=filtered_properties)


@app.route("/seller_dashboard")
def seller_dashboard():
    if "user_id" not in session or session.get("role") != "seller":
        flash("You must be logged in as a seller to view this page", "danger")
        return redirect(url_for("login"))

    user_properties = [p for p in properties if p["seller_id"] == session["user_id"]]
    return render_template("seller_dashboard.html", properties=user_properties)


@app.route("/post_property", methods=["GET", "POST"])
def post_property():
    if "user_id" not in session or session["role"] != "seller":
        flash("You must be logged in as a seller to post a property", "danger")
        return redirect(url_for("login"))

    form = PropertyForm()
    if form.validate_on_submit():
        image_file = None
        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                image_file = filename

        property_data = {
            "id": len(properties)
            + 1,  # Assigning a unique ID based on the length of the properties list
            "place": form.place.data,
            "area": form.area.data,
            "bedrooms": form.bedrooms.data,
            "bathrooms": form.bathrooms.data,
            "hospitals": form.hospitals.data,
            "colleges": form.colleges.data,
            "image": image_file,
            "seller_id": session["user_id"],
        }
        properties.append(property_data)
        flash("Property posted successfully!", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("property_form.html", form=form)


@app.route("/edit_property/<int:property_id>", methods=["GET", "POST"])
def edit_property(property_id):
    if "user_id" not in session or session["role"] != "seller":
        flash("You must be logged in as a seller to edit a property", "danger")
        return redirect(url_for("login"))

    property = next(
        (
            p
            for p in properties
            if p["id"] == property_id and p["seller_id"] == session["user_id"]
        ),
        None,
    )
    if not property:
        flash(
            "Property not found or you do not have permission to edit this property",
            "danger",
        )
        return redirect(url_for("seller_dashboard"))

    form = PropertyForm(data=property)
    if form.validate_on_submit():
        property["place"] = form.place.data
        property["area"] = form.area.data
        property["bedrooms"] = form.bedrooms.data
        property["bathrooms"] = form.bathrooms.data
        property["hospitals"] = form.hospitals.data
        property["colleges"] = form.colleges.data

        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                property["image"] = filename

        flash("Property updated successfully!", "success")
        return redirect(url_for("seller_dashboard"))

    return render_template("property_form.html", form=form, property_id=property_id)


@app.route("/delete_property/<int:property_id>", methods=["POST"])
def delete_property(property_id):
    if "user_id" not in session or session["role"] != "seller":
        flash("You must be logged in as a seller to delete a property", "danger")
        return redirect(url_for("login"))

    property = next(
        (
            p
            for p in properties
            if p["id"] == property_id and p["seller_id"] == session["user_id"]
        ),
        None,
    )
    if property:
        properties.remove(property)
        flash("Property deleted successfully!", "success")
    else:
        flash(
            "Property not found or you do not have permission to delete this property",
            "danger",
        )

    return redirect(url_for("seller_dashboard"))


@app.route("/interested/<int:property_id>")
def interested(property_id):
    if "user_id" not in session or session.get("role") != "buyer":
        flash("You must be logged in as a buyer to show interest", "danger")
        return redirect(url_for("login"))

    # Check if the property is a dummy property
    dummy_properties = [
        {
            "id": 1,
            "place": "Downtown",
            "area": 1200,
            "bedrooms": 3,
            "bathrooms": 2,
            "hospitals": 2,
            "colleges": 3,
            "image": "property1.jpg",
            "seller_id": "seller1@example.com",
        },
        {
            "id": 2,
            "place": "Uptown",
            "area": 900,
            "bedrooms": 2,
            "bathrooms": 1,
            "hospitals": 1,
            "colleges": 1,
            "image": "property2.jpg",
            "seller_id": "seller2@example.com",
        },
        {
            "id": 3,
            "place": "Suburb",
            "area": 1500,
            "bedrooms": 4,
            "bathrooms": 2,
            "hospitals": 3,
            "colleges": 2,
            "image": "property3.jpg",
            "seller_id": "seller3@example.com",
        },
    ]

    property = next((p for p in dummy_properties if p["id"] == property_id), None)
    if property:
        # Dummy property found, fetch dummy seller details
        seller = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "seller@example.com",
            "phone_number": "1234567890",
        }
        return render_template("seller_details.html", property=property, seller=seller)
    else:
        seller = next((u for u in users if u["email"] == property["seller_id"]), None)
        if seller:
            return render_template(
                "seller_details.html", property=property, seller=seller
            )
        else:
            flash("Seller details not found", "danger")
        return redirect(url_for("buyer_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
