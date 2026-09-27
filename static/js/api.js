export async function api(path, body, {method = body === undefined ? 'GET' : 'POST', signal} = {}) {
  const response = await fetch('/api' + path, {method, signal, headers: body === undefined ? {} : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) {const error = new Error(data.error || '连接暂不可用'); error.confirmedFailure = response.status >= 400 && response.status < 500; throw error;}
  return data;
}
export const workspacePath = id => `/workspaces/${id}`;
