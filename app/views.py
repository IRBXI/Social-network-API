from typing import List
from emoji import emojize
from app import app, db
from app.models import Users, Posts, Reactions, CustomJSONEncoder
from flask import request, Response, jsonify
import json


@app.post("/users/create")
def user_create() -> Response:
    # Checking the content type
    if request.content_type != "application/json":
        return jsonify(
            {
                "errors": {
                    "invalid_content_type": "The content type should be application/json"
                }
            }
        )

    data = request.get_json()

    # Validating the data
    validation_errors = Users.user_validation_errors(data)
    if validation_errors:
        return validation_errors

    user = Users(data["first_name"], data["last_name"], data["email"])

    # Adding the user to the database
    db.session.add(user)
    db.session.commit()

    return Response(
        json.dumps(user, cls=CustomJSONEncoder), mimetype="application/json"
    )


@app.get("/users/<int:user_id>")
def user_info(user_id: int) -> Response:
    # Checking whether a user with such id exists or not
    query_result = Users.query.get(user_id)
    if query_result:
        user: Users = query_result
        return Response(
            json.dumps(user, cls=CustomJSONEncoder), mimetype="application/json"
        )
    return jsonify(
        {"errors": {"invalid_user_id": "The user with such id doesn't exist"}}
    )


@app.post("/users/delete/<int:user_id>")
def delete_user(user_id: int) -> Response:
    # Checking whether a user with such id exists or not
    query_result = Users.query.get(user_id)
    if query_result:
        user: Users = query_result

        # Deleting all the posts
        # (There is code repetition here, but if I used the delete_post, delete_reaction functions
        # it would cause multiple requests to the database instead of 1)
        posts: List[Posts] = Posts.query.filter_by(author_id=user.id)
        for post in posts:
            # Deleting all the reactions from the post
            reactions: List[Reactions] = list(
                Reactions.query.filter_by(post_id=post.id)
            )
            for reaction in reactions:
                # Decreasing the user total reactions count
                user = Users.query.get(reaction.author_id)
                user.total_reactions -= 1

                # Decreasing the post total reactions count
                post = Posts.query.get(reaction.post_id)
                post.total_reactions -= 1

                # Deleting the reaction from the database
                db.session.delete(reaction)

            # Deleting the post from the database
            db.session.delete(post)

        # Deleting the user from the database
        db.session.delete(user)

        # Commiting all the change to the database
        db.session.commit()

        return Response()
    return jsonify(
        {"errors": {"invalid_user_id": "The user with such id doesn't exist"}}
    )


@app.post("/users/<int:user_id>/posts")
def user_posts(user_id: int) -> Response:
    # Checking whether a user with such id exists or not
    if Users.query.get(user_id):
        # Checking the content type
        if request.content_type != "application/json":
            return jsonify(
                {
                    "errors": {
                        "invalid_content_type": "The content type should be application/json"
                    }
                }
            )

        data = request.get_json()

        # Validating the data
        data_validation_errors = Users.sort_type_validation_errors(data)
        if data_validation_errors:
            return data_validation_errors

        if data["sort_type"] == "asc":
            posts: List[Posts] = list(
                Posts.query.filter_by(author_id=user_id).order_by(Posts.total_reactions)
            )
        else:
            posts: List[Posts] = list(
                Posts.query.filter_by(author_id=user_id).order_by(
                    Posts.total_reactions.desc()
                )
            )

        response = {"posts": posts}

        return Response(
            json.dumps(response, cls=CustomJSONEncoder), mimetype="application/json"
        )

    return jsonify(
        {"errors": {"invalid_user_id": "The user with such id doesn't exist"}}
    )


@app.post("/users/leaderboard")
def users_leaderboard() -> Response:
    data = request.get_json()

    # Validating the data
    data_validation_errors = Users.leaderboard_validation_errors(data)
    if data_validation_errors:
        return data_validation_errors

    return Users.get_leaderboard(data["data_type"], data["sort_type"])


@app.post("/posts/create")
def post_create() -> Response:
    # Checking the content type
    if request.content_type != "application/json":
        return jsonify(
            {
                "errors": {
                    "invalid_content_type": "The content type should be application/json"
                }
            }
        )

    data = request.get_json()

    # Validating the data
    validation_errors = Posts.post_validation_errors(data)
    if validation_errors:
        return validation_errors

    post = Posts(data["author_id"], data["text"])

    # Adding the post to the database
    db.session.add(post)
    db.session.commit()

    return Response(
        json.dumps(post, cls=CustomJSONEncoder), mimetype="application/json"
    )


@app.get("/posts/<int:post_id>")
def post_info(post_id: int) -> Response:
    # Checking whether a post with such id exists or not
    query_result = Posts.query.get(post_id)
    if query_result:
        post: Posts = query_result
        return Response(
            json.dumps(post, cls=CustomJSONEncoder), mimetype="application/json"
        )
    return jsonify(
        {"errors": {"invalid_post_id": "The post with such id doesn't exist"}}
    )


@app.post("/posts/delete/<int:post_id>")
def delete_post(post_id: int) -> Response:
    # Checking whether a post with such id exists or not
    query_result = Posts.query.get(post_id)
    if query_result:
        post: Posts = query_result

        # Deleting all the reactions from the post
        reactions: List[Reactions] = list(Reactions.query.filter_by(post_id=post_id))
        for reaction in reactions:
            # (There is code repetition here, but if I used the delete_reaction function
            # it would cause multiple requests to the database instead of 1)

            # Decreasing the user total reactions count
            user = Users.query.get(reaction.author_id)
            user.total_reactions -= 1

            # Decreasing the post total reactions count
            post = Posts.query.get(reaction.post_id)
            post.total_reactions -= 1

            # Deleting the reaction from the database
            db.session.delete(reaction)

        # Deleting the post from the database
        db.session.delete(post)

        # Commiting all the changes to the database
        db.session.commit()

        return Response()
    return jsonify(
        {"errors": {"invalid_post_id": "The post with such id doesn't exist"}}
    )


@app.post("/reactions/react/<int:post_id>")
def react_to_post(post_id: int) -> Response:
    # Checking the content type
    if request.content_type != "application/json":
        return jsonify(
            {
                "errors": {
                    "invalid_content_type": "The content type should be application/json"
                }
            }
        )

    data = request.get_json()

    # Validating the data
    validation_errors = Reactions.reaction_validation_errors(post_id, data)
    if validation_errors:
        return validation_errors

    reaction = Reactions(data["user_id"], post_id, emojize(data["reaction"]))

    # Adding the reaction to the database
    db.session.add(reaction)

    # Increasing the post total reactions count
    post = Posts.query.get(post_id)
    post.total_reactions += 1

    # Increasing the user total reactions count
    user = Users.query.get(data["user_id"])
    user.total_reactions += 1

    # Commiting all the changes to the database
    db.session.commit()

    return jsonify({"reaction_id": reaction.id, "reaction": reaction.reaction})


@app.get("/reactions/<int:reaction_id>")
def reaction_info(reaction_id: int) -> Response:
    # Checking whether a reaction with such id exists or not
    query_result = Reactions.query.get(reaction_id)
    if query_result:
        reaction: Reactions = query_result

        return Response(
            json.dumps(reaction, cls=CustomJSONEncoder), mimetype="application/json"
        )
    return jsonify(
        {"errors": {"invalid_reaction_id": "The reaction with such id doesn't exist"}}
    )


@app.post("/reactions/delete/<int:reaction_id>")
def delete_reaction(reaction_id: int) -> Response:
    # Checking whether a reaction with such id exists or not
    query_result = Reactions.query.get(reaction_id)
    if query_result:
        reaction: Reactions = query_result

        # Decreasing the user total reactions count
        user = Users.query.get(reaction.author_id)
        user.total_reactions -= 1

        # Decreasing the post total reactions count
        post = Posts.query.get(reaction.post_id)
        post.total_reactions -= 1

        # Deleting the reaction from the database
        db.session.delete(reaction)

        # Commiting all the changes to the database
        db.session.commit()

        return Response()
    return jsonify(
        {"errors": {"invalid_reaction_id": "The reaction with such id doesn't exist"}}
    )
