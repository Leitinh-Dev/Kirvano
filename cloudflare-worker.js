// Cloudflare Worker para fazer requisições ao Kirvano
// Deploy em: https://workers.cloudflare.com/

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // Verifica se é uma requisição para o checkout
  if (url.pathname === '/checkout') {
    const checkoutUrl = url.searchParams.get('url')
    if (!checkoutUrl) {
      return new Response(JSON.stringify({ error: 'URL não fornecida' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      })
    }
    
    // Faz requisição ao checkout
    const response = await fetch(checkoutUrl, {
      method: 'GET',
      headers: {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Priority': 'u=0, i',
        'Referer': 'https://pay.kirvano.com/',
        'Sec-CH-UA': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
      }
    })
    
    const html = await response.text()
    
    return new Response(html, {
      status: 200,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    })
  }
  
  // Verifica se é uma requisição de pagamento
  if (url.pathname === '/payment') {
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Método não permitido' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      })
    }
    
    const body = await request.json()
    const checkoutUrl = url.searchParams.get('checkout_url') || body.checkout_url
    
    // Remove checkout_url do body antes de enviar (não é necessário na API)
    const { checkout_url, ...paymentData } = body
    
    // Faz requisição de pagamento
    const response = await fetch('https://pay-api.kirvano.com/payment', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json',
        'Origin': 'https://pay.kirvano.com',
        'Priority': 'u=1, i',
        'Referer': checkoutUrl ? (checkoutUrl + '/') : 'https://pay.kirvano.com/',
        'Sec-CH-UA': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      },
      body: JSON.stringify(paymentData)
    })
    
    const result = await response.json()
    
    // Retorna com HTTP code incluído
    const responseData = {
      http_code: response.status,
      response: result
    }
    
    return new Response(JSON.stringify(responseData), {
      status: 200, // Sempre retorna 200 para o Worker, mas inclui o código real no JSON
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    })
  }
  
  // Verifica se é uma requisição para installments (validação de plan_uuid)
  if (url.pathname === '/installments') {
    const offerUuid = url.searchParams.get('offerUuid')
    const planUuid = url.searchParams.get('planUuid')
    const total = url.searchParams.get('total') || '59.9'
    const limit = url.searchParams.get('limit') || '12'
    
    if (!offerUuid || !planUuid) {
      return new Response(JSON.stringify({ error: 'Parâmetros faltando' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      })
    }
    
    const installmentsUrl = `https://7gevum3nv9.execute-api.us-east-1.amazonaws.com/production/installments?offerUuid=${offerUuid}&planUuid=${planUuid}&total=${total}&limit=${limit}`
    
    const response = await fetch(installmentsUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Origin': 'https://pay.kirvano.com',
        'Referer': 'https://pay.kirvano.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
      }
    })
    
    const result = await response.json()
    
    return new Response(JSON.stringify(result), {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    })
  }
  
  // Handle OPTIONS (CORS preflight)
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    })
  }
  
  return new Response(JSON.stringify({ error: 'Endpoint não encontrado' }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' }
  })
}

