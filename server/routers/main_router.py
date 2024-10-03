from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["Main"])


@router.get("/", response_class=HTMLResponse)
def get_main():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Clarity</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 0;
          background-color: #333;
        }
        header {
          background-color: #333;
          color: white;
          text-align: center;
          padding: 1em;
        }
        .container {
          max-width: 960px;
          margin: auto;
          padding: 2em;
        }
        .cta-button {
          background-color: blue;
          color: white;
          padding: 10px 20px;
          text-align: center;
          display: inline-block;
          border-radius: 5px;
          cursor: pointer;
        }
        .cta-button:hover {
          background-color: darkblue;
        }
      </style>
    </head>
    <body>
      <header>
        <h1>Welcome to Clarity Trading Platform</h1>
      </header>
      <div class="container">
        <h2>About Us</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
        <h2>Features</h2>
        <ul>
          <li>Easy to Use</li>
          <li>Highly Customizable</li>
          <li>Full Featured</li>
        </ul>
        <div>
          <a class="cta-button" href="#signup">Sign Up Now!</a>
        </div>
      </div>
      <script>
        // Add any JavaScript functionality if needed
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
