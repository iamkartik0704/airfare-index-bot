import os, re

for root, _, files in os.walk('src'):
    for f in files:
        if f.endswith('.tsx'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            if 'convex/react' in content or '_generated/api' in content:
                content = re.sub(r'import\s+\{.*?\}\s+from\s+"convex/react";\n', '', content)
                content = re.sub(r'import\s+\{\s*api\s*\}\s+from\s+"@/convex/_generated/api";\n', 'import { useApi } from "@/hooks/useApi";\n', content)
                content = re.sub(r'useQuery\(api\.apix\.(\w+)(?:,\s*\{[^}]*\})?\)', r'useApi("\1")', content)
                content = re.sub(r'useQuery\(api\.pipeline\.(\w+)\)', r'useApi("\1")', content)
                content = re.sub(r'useMutation\(api\.pipeline\.(\w+)\)', r'(() => async () => {})', content)
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f'Fixed {path}')
