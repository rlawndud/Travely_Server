using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;

namespace bitserver
{
    internal class Control
    {
        #region 싱글톤
        public static Control Instance { get; set; } = null;

        static Control()
        {
            Instance = new Control();
        }

        private Control()
        {

        }
        #endregion

        public void Dispose()
        {
        }

        private BitmapImage Imgload(string strpath)
        {
            try
            {
                FileInfo fio = new FileInfo(strpath);
                if (fio.Exists)
                {
                    BitmapImage img = new BitmapImage();

                    img.BeginInit();
                    img.CacheOption = BitmapCacheOption.OnLoad;
                    img.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
                    img.UriSource = new Uri(strpath, UriKind.RelativeOrAbsolute);
                    img.EndInit();

                    if (img.CanFreeze) img.Freeze();

                    return img;
                }
                else
                    return null;
            }
            catch
            {
                return null;
            }
        }

        public static string ImageToStringConvert(BitmapImage Bitmapimage)
        {
            //BitmapImage To Byte[] Data            
            MemoryStream memStream = new MemoryStream();
            JpegBitmapEncoder encoder = new JpegBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(Bitmapimage));
            encoder.Save(memStream);
            byte[] Image_BinaryData = memStream.GetBuffer();
            // BinaryData To StringData            
            string ImageString = Convert.ToBase64String(Image_BinaryData);
            return ImageString;
        }

        #region Service -> Control
        public byte[] RecvData(HttpListenerResponse response, string rawurl, string httpmethod, string result)
        {
            Console.WriteLine($"httpmethod = {httpmethod}\n");
            Console.WriteLine($"rawurl = {rawurl}\n");
            Console.WriteLine(result + "\n");

            if (httpmethod == "GET")
            {

            }
            else if (httpmethod == "POST")
            {
                if(rawurl == "/Member")
                {
                    return Insert_Member(response, result);
                }
            }
            else if (httpmethod == "PUT")
            {
            }
            else if (httpmethod == "DELETE")
            {
            }
            return null;
        }
        #endregion

        public byte[] Insert_Member(HttpListenerResponse response, string json_text)
        {
            try
            {
                

                string serializeJson = JsonConvert.SerializeObject(true);
                byte[] buffer = Encoding.UTF8.GetBytes(serializeJson);
                response.ContentLength64 = buffer.Length;
                response.StatusCode = (int)HttpStatusCode.OK;
                response.StatusDescription = "OK";
                return buffer;
            }
            catch (Exception ex)
            {
                byte[] buffer = Encoding.UTF8.GetBytes("");
                response.ContentLength64 = buffer.Length;
                response.StatusCode = (int)HttpStatusCode.NotFound;
                response.StatusDescription = ex.Message;
                return buffer;
            }
        }




    }
}
