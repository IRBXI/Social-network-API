import re
import emoji
import json
import os
import matplotlib

# Fixes the RuntimeError: "main thread is not in main loop",
# which occures during the proccess of saving the graph with plt.savefig()
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from app import db
from typing import Dict
from flask import Response, jsonify, send_file


class Users(db.Model):
    # Database model
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    total_reactions = db.Column(db.Integer, default=0)

    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    @staticmethod
    def validate_email(email: str) -> bool:
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return True
        return False

    @staticmethod
    def user_validation_errors(data: Dict) -> None | Response:
        """Returns None if there are not errors during the validation otherwise
        returns a Response with json containing all the error messages"""

        response: Dict[str, Dict] = {"errors": {}}

        # Validating the json format
        try:
            first_name = data["first_name"]
            last_name = data["last_name"]
            email = data["email"]
        except KeyError:
            response["errors"]["invalid_json_format"] = "json format is invalid"
            return jsonify(response)

        # Validating the types of variables
        for var, var_name, var_type in zip(
            (first_name, last_name, email),
            ("first_name", "last_name", "email"),
            (str, str, str),
        ):
            if not (isinstance(var, var_type)):
                response["errors"][
                    f"invalid_{var_name}_type"
                ] = f"{var_name} should be a {var_type.__name__}"

        # Validating the sizes of str variables according to database limits
        # (It isn't actually required if you are using a sqlite database,
        # because it ignores the length restrictions for varchar and just stores it as text)
        for var, var_name in zip(
            (first_name, last_name, email), ("first_name", "last_name", "email")
        ):
            if len(var) > 100:
                response["errors"][
                    f"invalid_{var_name}_length"
                ] = f"{var_name} should be less than 100 characters long"

        # Validating the email
        if ("invalid_email_type" not in response["errors"]) and (
            not Users.validate_email(email)
        ):
            response["errors"]["invalid_email_format"] = "email format is invalid"

        # Validating that there is no user with such email
        if len(list(Users.query.filter_by(email=email))) != 0:
            response["errors"]["invalid_email"] = "user with such email already exists"

        if len(response["errors"]) == 0:
            return None
        return jsonify(response)

    # Maybe it doesn't make sense for this function to be in Users class,
    # but I can't think of a better place for it to be right now
    @staticmethod
    def sort_type_validation_errors(data: Dict) -> None | Response:
        """Returns None if there are not errors during the validation otherwise
        returns a Response with json containing all the error messages"""

        response: Dict[str, Dict] = {"errors": {}}

        # Validating the json format
        try:
            sort_type = data["sort_type"]
        except KeyError:
            response["errors"]["invalid_json_format"] = "json format is invalid"
            return jsonify(response)

        # Validating the content of the variable
        if sort_type != "asc" and sort_type != "desc":
            response["errors"][
                "invalid_sort_type"
            ] = "sort_type should be a string containing either 'asc' or 'desc'"

        if len(response["errors"]) == 0:
            return None
        return jsonify(response)

    @staticmethod
    def leaderboard_validation_errors(data: Dict) -> None | Response:
        """Returns None if there are not errors during the validation otherwise
        returns a Response with json containing all the error messages"""

        # Validating the sort_type part of the request
        validation_errors = Users.sort_type_validation_errors(data)
        if validation_errors:
            response: Dict[str, Dict] = validation_errors.json
        else:
            response: Dict[str, Dict] = {"errors": {}}

        # Validating the json format for the type
        try:
            result_type = data["data_type"]
        except KeyError:
            response["errors"]["invalid_json_format"] = "json format is invalid"
            return jsonify(response)

        # Validating the content of the variable
        if result_type != "list" and result_type != "graph":
            response["errors"][
                "invalid_data_type"
            ] = "data_type should be a string containing either 'list' or 'graph'"

        if len(response["errors"]) == 0:
            return None
        return jsonify(response)

    @staticmethod
    def get_leaderboard(data_type: str, sort_type: str) -> Response:
        # Getting a list of users in the ascending or descending order
        if sort_type == "asc":
            users = list(Users.query.order_by(Users.total_reactions))
        else:
            users = list(Users.query.order_by(Users.total_reactions.desc()))

        match data_type:
            case "list":
                response = {"users": users}

                return Response(
                    json.dumps(response, cls=CustomJSONEncoder),
                    mimetype="application/json",
                )
            case "graph":
                # Preparing data for the graph
                users_reaction_count = np.array(
                    [user.total_reactions for user in users]
                )
                users_names_with_ids = np.array(
                    [
                        f"{user.first_name} {user.last_name} (id: {user.id})"
                        for user in users
                    ]
                )

                # Clearing the figure to prevent previous graph overriding the current one
                plt.clf()

                # Creating a graph from the data with matplotlib.pyplot
                plt.bar(users_names_with_ids, users_reaction_count, color="blue")
                plt.xticks(rotation=10)
                plt.xlabel("User")
                plt.ylabel("Reaction count")
                plt.title("Users leaderboard")
                plt.gcf().set_size_inches(8, 7)

                # Deleting the old graph if it exists
                if os.path.exists("static/images/users_leaderboard.png"):
                    os.remove("static/images/users_leaderboard.png")

                # Saving the new graph
                plt.savefig("app/static/images/users_leaderboard.png", dpi=100)

                return send_file("static/images/users_leaderboard.png")


class Posts(db.Model):
    # Database model
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    total_reactions = db.Column(db.Integer, default=0)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __init__(self, author_id: int, text: str) -> None:
        self.author_id = author_id
        self.text = text

    @staticmethod
    def post_validation_errors(data: Dict) -> None | Response:
        """Returns None if there are not errors during the validation otherwise
        returns a Response with json containing all the error messages"""

        response: Dict[str, Dict] = {"errors": {}}

        # Validating the json format
        try:
            author_id = data["author_id"]
            text = data["text"]
        except KeyError:
            response["errors"]["invalid_json_format"] = "json format is invalid"
            return jsonify(response)

        # Validating the types of variables
        for var, var_name, var_type in zip(
            (author_id, text), ("author_id", "text"), (int, str)
        ):
            if not (isinstance(var, var_type)):
                article = "an" if var_type is int else "a"
                response["errors"][
                    f"invalid_{var_name}_type"
                ] = f"{var_name} should be {article} {var_type.__name__}"

        # Validating that there is a user with such id
        if Users.query.get(author_id) is None:
            response["errors"]["invalid_author_id"] = "user with such id doesn't exist"

        if len(response["errors"]) == 0:
            return None
        return jsonify(response)


class Reactions(db.Model):
    # Database model
    id = db.Column(db.Integer, primary_key=True)
    reaction = db.Column(db.String(100))

    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __init__(self, author_id: int, post_id: int, reaction: str) -> None:
        self.author_id = author_id
        self.post_id = post_id
        self.reaction = reaction

    @staticmethod
    def reaction_validation_errors(post_id: int, data: Dict) -> None | Response:
        """Returns None if there are not errors during the validation otherwise
        returns a Response with json containing all the error messages"""

        response: Dict[str, Dict] = {"errors": {}}

        # Validating the json format
        try:
            user_id = data["user_id"]
            reaction = data["reaction"]
        except KeyError:
            response["errors"]["invalid_json_format"] = "json format is invalid"
            return jsonify(response)

        # Validating the types of variables
        for var, var_name, var_type in zip(
            (user_id, reaction), ("user_id", "reaction"), (int, str)
        ):
            if not (isinstance(var, var_type)):
                article = "an" if var_type is int else "a"
                response["errors"][
                    f"invalid_{var_name}_type"
                ] = f"{var_name} should be {article} {var_type.__name__}"

        # Validating that reaction is an emoji
        # emoji.is_emoji additionally checks
        # that the string contains only one emoji not multiple
        if ("invalid_reaction_type" not in response["errors"]) and (
            not (emoji.is_emoji(emoji.emojize(reaction)))
        ):
            response["errors"]["invalid_reaction"] = (
                "reaction should be a single emoji,"
                "or a string in the following format - :unicode_emoji_CLDR_short_name:"
            )

        # Validating that a post with such id exists
        if Posts.query.get(post_id) is None:
            response["errors"]["invalid_post_id"] = "post with such id doesn't exist"

        # Validating that a user with such id exists
        if Users.query.get(user_id) is None:
            response["errors"]["invalid_user_id"] = "user with such id doesn't exist"

        if len(response["errors"]) == 0:
            return None
        return jsonify(response)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Users):
            data = {
                "id": obj.id,
                "first_name": obj.first_name,
                "last_name": obj.last_name,
                "email": obj.email,
                "total_reactions": obj.total_reactions,
                "posts": [],
            }

            posts = Posts.query.filter_by(author_id=obj.id)

            for post in posts:
                data["posts"].append(post.text)

            return data
        if isinstance(obj, Posts):
            data = {
                "id": obj.id,
                "author_id": obj.author_id,
                "text": obj.text,
                "reactions": [],
            }

            reactions = Reactions.query.filter_by(post_id=obj.id)

            for reaction in reactions:
                data["reactions"].append(reaction.reaction)

            return data
        if isinstance(obj, Reactions):
            data = {
                "id": obj.id,
                "post_id": obj.post_id,
                "author_id": obj.author_id,
                "reaction": obj.reaction,
            }

            return data
        return super(CustomJSONEncoder, self).default(obj)
