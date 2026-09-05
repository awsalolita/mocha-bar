# AWS Cognito

Amazon Cognito provides authentication, authorization, and user management for web and mobile apps. 

---

## 1. Core Components: User Pools vs. Identity Pools

The most common point of confusion in Cognito is the difference between User Pools and Identity Pools.

### Cognito User Pools (Authentication / AuthN)
* **What it is:** A user directory. It handles sign-up, sign-in, password recovery, and MFA.
* **Output:** Upon successful login, Cognito returns three JWTs (JSON Web Tokens):
  1. **ID Token:** Contains user profile information (claims like email, name).
  2. **Access Token:** Used to authorize API calls (contains scopes and groups).
  3. **Refresh Token:** Used to get new ID and Access tokens without re-authenticating.
* **Use Case:** "I need my users to log in with an email/password or via Google/Facebook to access my application."

### Cognito Identity Pools (Authorization / AuthZ)
* **What it is:** A credential broker. It exchanges tokens (from User Pools, Google, SAML) for **temporary, scoped AWS IAM credentials**.
* **Output:** AWS Access Key, Secret Key, and Session Token.
* **Use Case:** "My frontend mobile app needs to directly upload a file to an S3 bucket or query a DynamoDB table."

> **Hint:** You often use both together! A user logs into a **User Pool** to get a JWT, then passes that JWT to an **Identity Pool** to get IAM credentials to access AWS services directly.

---

## 2. App Client Types

To interact with a User Pool, you must create an **App Client**.

1. **Confidential Client (Backend / Web Server App)**
   * **Requires:** A `Client Secret`.
   * **Use Case:** Server-side applications (like NodeJS or Python backends) that can securely store the secret.

2. **Public Client (SPA / Mobile App)**
   * **Requires:** NO Client Secret. (Secrets embedded in mobile apps or SPAs can easily be extracted).
   * **Security:** Instead of a secret, it uses **PKCE** (Proof Key for Code Exchange) during the OAuth flow to ensure the entity that requested the login is the one receiving the token.
   * **Use Case:** React/Vue apps, iOS/Android apps.

---

## 3. Integrations

Cognito integrates natively with several AWS networking and API services to easily secure your endpoints without writing custom JWT validation code.

### A. API Gateway Integration
You can protect your API Gateway REST/HTTP APIs using Cognito in two ways:

1. **Cognito User Pool Authorizer (Native)**
   * You configure API Gateway to point to your User Pool.
   * The client passes the `Authorization: Bearer <ID or Access Token>` header.
   * API Gateway validates the JWT signature and expiration automatically.
   * *Limitation:* It only checks if the token is valid, not fine-grained permissions.

2. **Lambda Authorizer**
   * If you need custom logic (e.g., checking if a user has paid for a specific tier in your database), you pass the token to a Lambda Authorizer which verifies the token and makes complex authorization decisions before allowing the request through.

### B. Application Load Balancer (ALB) Integration
ALB natively supports integrating with Cognito for web applications. 
* **How it works:** You add an **Authenticate** action to an ALB Listener Rule.
* **Flow:** 
  1. User accesses `myapp.com`.
  2. ALB redirects the unauthenticated user to the Cognito Hosted UI.
  3. User logs in, Cognito redirects back to ALB.
  4. ALB validates the token and forwards the request to your Target Group (e.g., an ECS container).
* **The Magic:** ALB passes the user information to your backend via HTTP headers (`x-amzn-oidc-data`, `x-amzn-oidc-identity`). Your backend doesn't need to implement OAuth flows; it just reads the headers!

---

## 4. Important Hints & Best Practices

* **Immutable Attributes:** When creating a User Pool, you must decide which standard attributes (like `email`, `sub`) are required. **This cannot be changed later.** If you mess this up, you have to create a brand new User Pool and migrate users.
* **Lambda Triggers:** Cognito allows you to attach Lambda functions to various lifecycle events:
  * *Pre Sign-up:* Auto-confirm certain domains or block specific emails.
  * *Post Confirmation:* Add the new user to a database (like DynamoDB or RDS).
  * *Pre Token Generation:* Inject custom claims (like tenant ID or roles) into the JWT before it is sent to the user.
* **Groups:** Use Cognito Groups to implement RBAC (Role-Based Access Control). Assign an IAM Role to a Group, and users in that group will inherit those permissions when using an Identity Pool.
* **Custom Attributes:** You can add custom attributes (e.g., `custom:tenant_id`). Note that custom attributes cannot be marked as "required", and they always have the `custom:` prefix.
* **Hosted UI:** Cognito provides a pre-built, customizable web UI for login/signup. It saves a lot of development time, though the styling options are somewhat limited.
