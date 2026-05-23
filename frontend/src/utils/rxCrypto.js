const RX_PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA2C3e6i+jWejZNIdXiH9x
TDQ+GhJXw8U5AO12GjiXZCiJ29Kb20/EUXcBQ0DRYjMyOJsE15Rlt6gEU8nSHCWV
5+RdEmQO1v0sfNen4Q08hr5bkaF1qsrWukthoR3u6/UDEadD4FMi4rakP3as2zDf
mRPbfbSOSvXWQPl04ojBYS74CrIB+5ZpNl7sRGMdG7D86nEm1wKQMBaFYsmfnBO2
lqLbx/1fqBSVctyFK4KfeHDPcUhm1V/33FrgMTgfPBwGap4pc78YaRKQAhptpHUZ
xuZHzJlOR8zp0XPv2d8CzgammeJsSI2DH3upOga7p5x2tLgW4q6i6m2cUKrl8WR6
xg9tlrHD10xKNz27SbKtbEacYjfXNvxpOYtBg1ubQDNNLYV6NL7oKsWmSmUXKv1i
ekgo0lcp/iKkv0Up2u6/oxsb/KTmUz2IcXJ5zSFsXUiovl4aAj/8BAz4vc2wCiVB
6CxMnaQEJK8xX0fkWwt1i6UC0sIKyYYAmBDlxusQkQJxlZ3TB2A+XUkQBrPEGWvQ
PQ1mUkkPUyDoRQmE4bLN/oZ+DrMnhCUd0hOeTb183/HTu8YKnMWWDzjcGB//6owq
h+hmTjxEHkZECsNtj9qo7PlxHcLAwUHcr6zx3NX2UbIvZhLPL/fxCGEwu18yDIFG
lWvcCPWuBPtF01p0vDTbxgkCAwEAAQ==
-----END PUBLIC KEY-----`;

function pemToDer(pem) {
  const b64 = pem
    .replace('-----BEGIN PUBLIC KEY-----', '')
    .replace('-----END PUBLIC KEY-----', '')
    .replace(/\s+/g, '');
  const raw = window.atob(b64);
  const len = raw.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = raw.charCodeAt(i);
  }
  return bytes.buffer;
}

export async function encryptForRX(value) {
  try {
    const keyData = pemToDer(RX_PUBLIC_KEY_PEM);
    const key = await window.crypto.subtle.importKey(
      'spki',
      keyData,
      {
        name: 'RSA-OAEP',
        hash: 'SHA-256',
      },
      false,
      ['encrypt']
    );

    const toEncode = JSON.stringify(value);
    const encoded = new TextEncoder().encode(toEncode);
    const encrypted = await window.crypto.subtle.encrypt(
      {
        name: 'RSA-OAEP',
      },
      key,
      encoded
    );

    // Convert to base64
    const encryptedBytes = new Uint8Array(encrypted);
    let binary = '';
    const len = encryptedBytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(encryptedBytes[i]);
    }
    return window.btoa(binary);
  } catch (error) {
    console.error('RSA Encryption failed:', error);
    throw error;
  }
}
