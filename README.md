# AT SMS

简简单单一个通过AT指令控制Air780E的程序，只能接受短信。暂时没写通知功能，直接看日志就行。

## 依赖

- Python 3.9+
- pyserial==3.5
- loguru==0.6.04

## 用法

```shell
python main.py -p [端口] -b [波特率]
```

其中，`[端口]`和`[波特率]`是可选的，如果不指定，程序会自动寻找可用的端口并使用115200波特率。

## 免责声明

此短信接收程序仅供个人使用，作者（或开发者）不对任何因使用此程序导致的任何直接或间接的损失、责任或损害承担任何法律责任。使用此程序之前，请充分了解所使用的短信服务提供商的服务条款和隐私策略。作者（或开发者）不对使用此程序导致的任何个人信息泄漏负责。用户应对使用此程序时的合法性、合规性和道德性负责，并确保不侵犯他人的权利。作者（或开发者）保留随时变更或终止此程序的权利。通过下载、安装或使用此程序，即表示您同意本免责声明。

## LICENSE

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.