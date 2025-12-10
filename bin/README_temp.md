java -cp $CLASSPATH \
     -Djava.library.path=/mnt/c/Users/hoang/Code/FIL-based-IDS-using-hybrid-supervised-and-unsupervised-models/Data_Extract/ModifiedCICFlowMeter/lib/native \
     PcapInterfaceTester

$APP_HOME="C:\Users\hoang\Code\FIL-based-IDS-using-hybrid-supervised-and-unsupervised-models\Data_Extract\ModifiedCICFlowMeter"
$CLASSPATH = (Get-ChildItem -Path "$APP_HOME\lib" -Filter "*.jar" | Select-Object -ExpandProperty FullName) -join ';'
$LIB="C:/Users/hoang/Code/FIL-based-IDS-using-hybrid-supervised-and-unsupervised-models/Data_Extract/ModifiedCICFlowMeter/lib/native"

cp target/*.jar lib/

sudo update-alternatives --config java


