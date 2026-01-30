"""
Platform-specific posting functions for LinkedIn, Reddit, and Email
"""
import requests
from typing import Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64

def post_to_linkedin(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to LinkedIn using LinkedIn API
    
    Args:
        content: Content to post
        credentials: LinkedIn API credentials (access_token, etc.)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    try:
        access_token = credentials.get('access_token')
        if not access_token:
            return {
                'success': False,
                'message': 'LinkedIn access token is required'
            }
        
        # LinkedIn API endpoint for posting
        api_url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        # Build LinkedIn post payload
        payload = {
            "author": f"urn:li:person:{credentials.get('person_id', '')}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # If image is provided, add it to the post
        if image_url:
            # Note: LinkedIn requires uploading image first, then referencing it
            # This is a simplified version - in production, upload image first
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            return {
                'success': True,
                'message': 'Content posted to LinkedIn successfully',
                'data': response.json()
            }
        else:
            return {
                'success': False,
                'message': f'Failed to post to LinkedIn: {response.text}',
                'status_code': response.status_code
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error posting to LinkedIn: {str(e)}'
        }


def post_to_reddit(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to Reddit using Reddit API
    
    Args:
        content: Content to post
        credentials: Reddit API credentials (client_id, client_secret, username, password, subreddit)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    try:
        client_id = credentials.get('client_id')
        client_secret = credentials.get('client_secret')
        username = credentials.get('username')
        password = credentials.get('password')
        subreddit = credentials.get('subreddit', 'test')
        
        if not all([client_id, client_secret, username, password]):
            return {
                'success': False,
                'message': 'Reddit credentials incomplete. Need: client_id, client_secret, username, password'
            }
        
        # Step 1: Get access token
        auth_url = "https://www.reddit.com/api/v1/access_token"
        auth_response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data={
                'grant_type': 'password',
                'username': username,
                'password': password
            },
            headers={'User-Agent': 'CampaignForge/1.0'}
        )
        
        if auth_response.status_code != 200:
            return {
                'success': False,
                'message': f'Failed to authenticate with Reddit: {auth_response.text}'
            }
        
        access_token = auth_response.json().get('access_token')
        
        # Step 2: Post to Reddit
        api_url = f"https://oauth.reddit.com/api/submit"
        headers = {
            'Authorization': f'bearer {access_token}',
            'User-Agent': 'CampaignForge/1.0'
        }
        
        # Split content into title and text (Reddit requires title)
        lines = content.split('\n', 1)
        title = lines[0][:300]  # Reddit title max 300 chars
        text = lines[1] if len(lines) > 1 else content
        
        payload = {
            'sr': subreddit,
            'title': title,
            'text': text,
            'kind': 'self'  # text post
        }
        
        # If image URL provided, use link post instead
        if image_url:
            payload['kind'] = 'link'
            payload['url'] = image_url
            payload['text'] = ''  # Remove text for link posts
        
        response = requests.post(api_url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': f'Content posted to r/{subreddit} successfully',
                'data': response.json()
            }
        else:
            return {
                'success': False,
                'message': f'Failed to post to Reddit: {response.text}',
                'status_code': response.status_code
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error posting to Reddit: {str(e)}'
        }


def post_to_email(content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Send content via Email using SMTP
    
    Args:
        content: Content to send
        credentials: Email credentials (smtp_server, smtp_port, email, password, recipient_email)
        image_url: Optional image URL to attach
    
    Returns:
        Response dict with success status
    """
    try:
        smtp_server = credentials.get('smtp_server', 'smtp.gmail.com')
        smtp_port = credentials.get('smtp_port', 587)
        email = credentials.get('email')
        password = credentials.get('password')
        recipient_email = credentials.get('recipient_email')
        subject = credentials.get('subject', 'Marketing Content')
        
        if not all([email, password, recipient_email]):
            return {
                'success': False,
                'message': 'Email credentials incomplete. Need: email, password, recipient_email'
            }
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add text content
        text_content = MIMEText(content, 'plain')
        msg.attach(text_content)
        
        # Add HTML version
        html_content = f"""
        <html>
          <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
              <h2>{subject}</h2>
              <div style="line-height: 1.6; color: #333;">
                {content.replace(chr(10), '<br>')}
              </div>
            </div>
          </body>
        </html>
        """
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # If image URL provided, fetch and attach image
        if image_url:
            try:
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code == 200:
                    img = MIMEImage(img_response.content)
                    img.add_header('Content-Disposition', 'attachment', filename='marketing_image.jpg')
                    msg.attach(img)
            except Exception as e:
                print(f"Warning: Could not attach image: {str(e)}")
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email, password)
        server.send_message(msg)
        server.quit()
        
        return {
            'success': True,
            'message': f'Email sent to {recipient_email} successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending email: {str(e)}'
        }


def post_to_platform(platform: str, content: str, credentials: Dict, image_url: Optional[str] = None) -> Dict:
    """
    Post content to the specified platform
    
    Args:
        platform: Platform name (LinkedIn, Reddit, Email)
        content: Content to post
        credentials: Platform-specific credentials
        image_url: Optional image URL
    
    Returns:
        Response dict with success status
    """
    platform = platform.lower()
    
    if platform == 'linkedin':
        return post_to_linkedin(content, credentials, image_url)
    elif platform == 'reddit':
        return post_to_reddit(content, credentials, image_url)
    elif platform == 'email':
        return post_to_email(content, credentials, image_url)
    else:
        return {
            'success': False,
            'message': f'Platform {platform} posting not yet implemented'
        }
