def load_prompt_template(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to load prompt template: {e}")
            return ""