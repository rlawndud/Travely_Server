using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;

namespace bitserver
{
    internal class Program
    {
        private Control _control = Control.Instance;
        private HttpListener httpListener = null;
        private int port = 80;
        // 관리자 컨솔에서 아래 주소를 등록해야 한다. 
        //netsh http add urlacl url=http://+:8686/ user=everyone
        public void serverInit()
        {
            if (httpListener == null)
            {
                httpListener = new HttpListener();
                httpListener.Prefixes.Add(string.Format($"http://+:{port}/"));
                serverStart();
            }
        }

        private void serverStart()
        {

            if (!httpListener.IsListening)
            {
                httpListener.Start();
                Console.WriteLine("Server is started");

                Task.Factory.StartNew(() =>
                {
                    while (httpListener != null)
                    {
                        try
                        {
                            HttpListenerContext context = this.httpListener.GetContext();

                            string rawurl = context.Request.RawUrl;
                            string httpmethod = context.Request.HttpMethod;

                            // 위 2가지 를 베이스로 RestAPI 파서를 구현한다. 
                            // 기능 호출은 POST
                            // 상태 확인은 GET

                            string result = "";
                            using (var reader = new StreamReader(context.Request.InputStream,
                                         context.Request.ContentEncoding))
                            {
                                result += reader.ReadToEnd();
                            };
                            Console.WriteLine($"httpmethod = {httpmethod}\n");
                            Console.WriteLine($"rawurl = {rawurl}\n");
                            Console.WriteLine(result + "\n");

                            byte[] buffer = _control.RecvData(context.Response, rawurl, httpmethod, result);

                            using (Stream output = context.Response.OutputStream)
                            {
                                output.Write(buffer, 0, buffer.Length);
                            }

                            context.Response.Close();

                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine(ex.ToString());
                        }

                    }
                });

            }
        }

        static void Main(string[] args)
        {
            //관리자모드로 실행
            new Program().serverInit();

            Console.WriteLine("종료하려면 아무키나 누르세요.");
            Console.ReadLine();
        }
    }
}
