import re

file_path = "/Users/samaysamrat/bankcctv/frontend/src/components/landing/marketing/Pricing.tsx"

with open(file_path, "r") as f:
    content = f.read()

# Change pricing
content = content.replace('heading="Pricing"', 'heading="License"')
content = content.replace('subheading="Enterprise License. Unlimited Cameras."', 'subheading="Open Source. Unlimited Cameras."')
content = content.replace('description="Deploy across unlimited nodes with a single enterprise license. Built for city-scale."', 'description="Deploy across unlimited nodes for free. Built for city-scale law enforcement."')

content = content.replace('ONE PLAN', 'FREE TIER')
content = content.replace('>$99<', '>$0<')
content = content.replace('> / month<', '> / forever<')
content = content.replace('Plus the AI plan you already pay for. ChatGPT recommended. Claude, Codex, Grok, and 8 others work too.', 'Completely open-source and free for government agencies and hackathon evaluations. No hidden token markups.')
content = content.replace('Cancel anytime. Keep access through your billing period. The current period is non-refundable. Isolated infra is provisioned when you sign up.', 'Download the code from GitHub and deploy on your own servers. Isolated infrastructure ensures 100% data privacy.')

with open(file_path, "w") as f:
    f.write(content)

print("Pricing updated successfully.")
