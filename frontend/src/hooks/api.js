export async function api(path, options) {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}
