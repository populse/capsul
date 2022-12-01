class Backend {};
{%- for name, method in backend_methods.items() %}
Backend.prototype.{{name}} = function ({% for p in method._params %}{{p}}, {% endfor %}{% if method._return %}handler{% endif %}) {
  {%- if method._return %}
      const args = Object.values(arguments).slice(0,-1);
  {%- else %}
    const args = Object.values(arguments);
  {%- endif %}
  const f = fetch("{{base_url}}/backend/{{name}}", {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(args)
  });
  {%- if method._return %}
    const r = f.then(response => response.json());
    r.then(data => handler(data));
  {%- endif %}
}
{%- endfor %}

var backend = null;
window.addEventListener("load", (event) => {
  backend = new Backend();
  event.currentTarget.dispatchEvent(backend_ready);
});
