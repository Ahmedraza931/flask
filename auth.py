"""
Authentication routes for Google OAuth integration
"""
import os
from flask import Blueprint, redirect, url_for, session, jsonify, request
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from src.models.user import db, User

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)

# Google OAuth configuration
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_CLIENT_ID", "your-google-client-id"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
    scope=["openid", "email", "profile"],
    storage=SQLAlchemyStorage(OAuthConsumerMixin, db.session, user=lambda: session.get('user_id'))
)

@auth_bp.route('/login')
def login():
    """Initiate Google OAuth login"""
    if not google.authorized:
        return redirect(url_for("google.login"))
    
    # Get user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({"error": "Failed to fetch user info from Google"}), 400
    
    info = resp.json()
    email = info.get("email")
    name = info.get("name")
    picture = info.get("picture")
    
    # Find or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name=name,
            profile_picture=picture
        )
        db.session.add(user)
        db.session.commit()
    else:
        # Update user info
        user.name = name
        user.profile_picture = picture
        db.session.commit()
    
    # Store user in session
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_name'] = user.name
    
    return redirect('/')

@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    return redirect('/')

@auth_bp.route('/user')
def get_current_user():
    """Get current logged-in user info"""
    if 'user_id' not in session:
        return jsonify({"authenticated": False}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({"authenticated": False}), 401
    
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_picture": user.profile_picture
        }
    })

@auth_bp.route('/check')
def check_auth():
    """Check if user is authenticated"""
    return jsonify({
        "authenticated": 'user_id' in session,
        "user_id": session.get('user_id'),
        "user_email": session.get('user_email'),
        "user_name": session.get('user_name')
    })

